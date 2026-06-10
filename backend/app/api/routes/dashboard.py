from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.db.models import Email, EmailStatus, EmailCategory, Urgency

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Returns counts for the mission control inbox dashboard.
    """
    # Total emails
    total_result = await db.execute(select(func.count(Email.id)))
    total = total_result.scalar()

    # By status
    pending_result = await db.execute(
        select(func.count(Email.id)).where(Email.status == EmailStatus.received)
    )
    pending = pending_result.scalar()

    processing_result = await db.execute(
        select(func.count(Email.id)).where(Email.status == EmailStatus.processing)
    )
    processing = processing_result.scalar()

    replied_result = await db.execute(
        select(func.count(Email.id)).where(Email.status == EmailStatus.replied)
    )
    replied = replied_result.scalar()

    escalated_result = await db.execute(
        select(func.count(Email.id)).where(Email.status == EmailStatus.escalated)
    )
    escalated = escalated_result.scalar()

    ignored_result = await db.execute(
        select(func.count(Email.id)).where(Email.status == EmailStatus.ignored)
    )
    ignored = ignored_result.scalar()

    # Critical emails
    critical_result = await db.execute(
        select(func.count(Email.id)).where(Email.urgency == Urgency.critical)
    )
    critical = critical_result.scalar()

    # Spam filtered
    spam_result = await db.execute(
        select(func.count(Email.id)).where(Email.is_spam_heuristic == True)
    )
    spam = spam_result.scalar()

    # Needs human
    human_result = await db.execute(
        select(func.count(Email.id)).where(Email.requires_human == True)
    )
    needs_human = human_result.scalar()

    # Security threats
    security_result = await db.execute(
        select(func.count(Email.id)).where(Email.is_security_threat == True)
    )
    security_threats = security_result.scalar()

    # Category breakdown
    category_result = await db.execute(
        select(Email.category, func.count(Email.id))
        .where(Email.category != None)
        .group_by(Email.category)
    )
    category_breakdown = {
        str(row[0].value) if row[0] else "Unknown": row[1]
        for row in category_result.all()
    }

    return {
        "total": total,
        "by_status": {
            "pending": pending,
            "processing": processing,
            "replied": replied,
            "escalated": escalated,
            "ignored": ignored,
        },
        "critical": critical,
        "spam_filtered": spam,
        "needs_human": needs_human,
        "security_threats": security_threats,
        "category_breakdown": category_breakdown,
    }

@router.get("/api/emails")
async def get_all_emails(
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Returns all emails for the inbox view."""
    from sqlalchemy import desc

    query = select(Email).order_by(desc(Email.timestamp))

    if status == 'human':
        query = query.where(Email.requires_human == True)
    elif status == 'escalated':
        query = query.where(Email.status == EmailStatus.escalated)
    elif status == 'replied':
        query = query.where(Email.status == EmailStatus.replied)
    elif status == 'spam':
        query = query.where(Email.is_spam_heuristic == True)

    result = await db.execute(query)
    emails = result.scalars().all()

    return {
        "emails": [
            {
                "id": e.id,
                "message_id": e.message_id,
                "sender": e.sender,
                "subject": e.subject,
                "body": (e.body or "")[:200],
                "timestamp": str(e.timestamp),
                "category": e.category.value if e.category else None,
                "sentiment": e.sentiment.value if e.sentiment else None,
                "sentiment_score": e.sentiment_score,
                "urgency": e.urgency.value if e.urgency else None,
                "requires_human": e.requires_human,
                "status": e.status.value if e.status else None,
                "is_spam": e.is_spam_heuristic,
                "is_internal": e.is_internal,
                "is_security_threat": e.is_security_threat,
                "thread_id": e.thread_id,
                "confidence": e.confidence,
            }
            for e in emails
        ],
        "total": len(emails)
    }