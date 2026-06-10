from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Email, Action
from app.agent.agent import run_agent

router = APIRouter()


@router.post("/agent/run/{email_id}")
async def run_agent_on_email(
    email_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Run the autonomous agent on a specific email.
    Executes tools and stores reasoning trace.
    """
    result = await db.execute(
        select(Email).where(Email.id == email_id)
    )
    email = result.scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=404, detail={
            "error_code": "EMAIL_NOT_FOUND",
            "message": f"No email found with id: {email_id}",
            "details": None
        })

    heuristic_flags = {
        "is_spam_heuristic": email.is_spam_heuristic,
        "is_internal": email.is_internal,
        "is_security_threat": email.is_security_threat,
        "is_gdpr": False,
        "is_legal": False,
        "is_urgent": False,
    }

    classification = {
        "category": email.category.value if email.category else "Other",
        "urgency": email.urgency.value if email.urgency else "Medium",
        "sentiment": email.sentiment.value if email.sentiment else "Neutral",
        "requires_human": email.requires_human,
        "escalation_reason": email.escalation_reason,
    }

    result = await run_agent(
        email_id=email_id,
        sender=email.sender,
        subject=email.subject or "",
        body=email.body or "",
        heuristic_flags=heuristic_flags,
        classification=classification,
        db=db,
        dry_run=False,
    )

    # Store reasoning trace on the latest action
    action_result = await db.execute(
        select(Action)
        .where(Action.email_id == email_id)
        .order_by(Action.id.desc())
    )
    latest_action = action_result.scalar_one_or_none()

    if latest_action:
        latest_action.agent_reasoning_log = result["reasoning_trace"]
        await db.commit()

    return result


@router.post("/agent/dry-run/{email_id}")
async def dry_run_agent(
    email_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Run agent in planning mode — shows reasoning trace without executing actions.
    """
    result = await db.execute(
        select(Email).where(Email.id == email_id)
    )
    email = result.scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=404, detail={
            "error_code": "EMAIL_NOT_FOUND",
            "message": f"No email found with id: {email_id}",
            "details": None
        })

    heuristic_flags = {
        "is_spam_heuristic": email.is_spam_heuristic,
        "is_internal": email.is_internal,
        "is_security_threat": email.is_security_threat,
        "is_gdpr": False,
        "is_legal": False,
        "is_urgent": False,
    }

    classification = {
        "category": email.category.value if email.category else "Other",
        "urgency": email.urgency.value if email.urgency else "Medium",
        "sentiment": email.sentiment.value if email.sentiment else "Neutral",
        "requires_human": email.requires_human,
        "escalation_reason": email.escalation_reason,
    }

    result = await run_agent(
        email_id=email_id,
        sender=email.sender,
        subject=email.subject or "",
        body=email.body or "",
        heuristic_flags=heuristic_flags,
        classification=classification,
        db=db,
        dry_run=True,
    )

    return result