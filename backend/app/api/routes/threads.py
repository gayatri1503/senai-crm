from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Email, Thread, Contact, Action

router = APIRouter()


@router.get("/threads/{contact_email}")
async def get_thread_by_contact(
    contact_email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns all threads and emails for a contact.
    Full conversation history with actions and agent logs.
    """
    # Get contact
    contact_result = await db.execute(
        select(Contact).where(Contact.email == contact_email)
    )
    contact = contact_result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=404, detail={
            "error_code": "CONTACT_NOT_FOUND",
            "message": f"No contact found for email: {contact_email}",
            "details": None
        })

    # Get all threads for this contact
    threads_result = await db.execute(
        select(Thread)
        .where(Thread.sender_email == contact_email)
        .order_by(Thread.last_updated_at.desc())
    )
    threads = threads_result.scalars().all()

    thread_data = []
    for thread in threads:
        # Get emails in thread
        emails_result = await db.execute(
            select(Email)
            .where(Email.thread_id == thread.thread_id)
            .order_by(Email.timestamp)
        )
        emails = emails_result.scalars().all()

        emails_data = []
        for email in emails:
            # Get actions for this email
            actions_result = await db.execute(
                select(Action).where(Action.email_id == email.id)
            )
            actions = actions_result.scalars().all()

            emails_data.append({
                "id": email.id,
                "message_id": email.message_id,
                "sender": email.sender,
                "subject": email.subject,
                "body": email.body,
                "timestamp": str(email.timestamp),
                "category": email.category.value if email.category else None,
                "sentiment": email.sentiment.value if email.sentiment else None,
                "sentiment_score": email.sentiment_score,
                "urgency": email.urgency.value if email.urgency else None,
                "requires_human": email.requires_human,
                "escalation_reason": email.escalation_reason,
                "suggested_reply": email.suggested_reply,
                "confidence": email.confidence,
                "status": email.status.value if email.status else None,
                "is_spam": email.is_spam_heuristic,
                "is_internal": email.is_internal,
                "is_security_threat": email.is_security_threat,
                "raw_entities": email.raw_entities,
                "actions": [
                    {
                        "id": a.id,
                        "action_type": a.action_type.value if a.action_type else None,
                        "proposed_content": a.proposed_content,
                        "is_approved": a.is_approved,
                        "approved_by": a.approved_by,
                        "executed_at": str(a.executed_at) if a.executed_at else None,
                        "agent_reasoning_log": a.agent_reasoning_log,
                    }
                    for a in actions
                ]
            })

        thread_data.append({
            "id": thread.id,
            "thread_id": thread.thread_id,
            "subject": thread.subject,
            "status": thread.status.value if thread.status else None,
            "first_seen_at": str(thread.first_seen_at),
            "last_updated_at": str(thread.last_updated_at),
            "assigned_to": thread.assigned_to,
            "email_count": len(emails_data),
            "emails": emails_data,
        })

    return {
        "contact": {
            "email": contact.email,
            "name": contact.name,
            "company": contact.company,
            "status": contact.status.value if contact.status else None,
            "account_value": contact.account_value,
            "churn_risk_score": contact.churn_risk_score,
            "created_at": str(contact.created_at),
            "last_contact_at": str(contact.last_contact_at),
        },
        "threads": thread_data,
        "total_threads": len(thread_data),
    }