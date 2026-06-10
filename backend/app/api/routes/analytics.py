from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
from app.db.database import get_db
from app.db.models import Email, Contact, Thread

router = APIRouter()


@router.get("/analytics/sentiment-trend")
async def get_sentiment_trend(
    sender: str = Query(None, description="Filter by sender email"),
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Time-series sentiment data per sender or global.
    Detects sentiment deterioration — 3+ consecutive negative emails.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            Email.sender,
            Email.timestamp,
            Email.sentiment_score,
            Email.sentiment,
            Email.thread_id,
            Email.subject,
        )
        .where(Email.sentiment_score != None)
        .where(Email.timestamp >= cutoff)
        .order_by(Email.sender, Email.timestamp)
    )

    if sender:
        query = query.where(Email.sender == sender)

    result = await db.execute(query)
    rows = result.all()

    # Group by sender
    sender_data = {}
    for row in rows:
        s = row.sender
        if s not in sender_data:
            sender_data[s] = []
        sender_data[s].append({
            "timestamp": str(row.timestamp),
            "sentiment_score": row.sentiment_score,
            "sentiment": row.sentiment.value if row.sentiment else None,
            "thread_id": row.thread_id,
            "subject": row.subject,
        })

    # Detect deterioration and compute stats per sender
    trends = []
    for s, data_points in sender_data.items():
        avg_score = sum(d["sentiment_score"] for d in data_points) / len(data_points)

        # Moving average (window of 3)
        moving_avg = []
        for i in range(len(data_points)):
            window = data_points[max(0, i-2):i+1]
            avg = sum(w["sentiment_score"] for w in window) / len(window)
            moving_avg.append(round(avg, 4))

        # Detect 3+ consecutive negative emails
        consecutive_negative = 0
        max_consecutive_negative = 0
        for dp in data_points:
            if dp["sentiment_score"] < 0:
                consecutive_negative += 1
                max_consecutive_negative = max(
                    max_consecutive_negative, consecutive_negative
                )
            else:
                consecutive_negative = 0

        deteriorating = max_consecutive_negative >= 3

        trends.append({
            "sender": s,
            "data_points": data_points,
            "moving_average": moving_avg,
            "average_sentiment_score": round(avg_score, 4),
            "total_emails_analysed": len(data_points),
            "max_consecutive_negative": max_consecutive_negative,
            "deteriorating": deteriorating,
            "alert": deteriorating,
        })

    # Sort by most deteriorating first
    trends.sort(key=lambda x: x["average_sentiment_score"])

    return {
        "period_days": days,
        "sender_filter": sender,
        "total_senders": len(trends),
        "deteriorating_senders": [t for t in trends if t["deteriorating"]],
        "all_trends": trends,
    }


@router.get("/analytics/category-breakdown")
async def get_category_breakdown(
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """Category distribution over configurable date range."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(Email.category, func.count(Email.id))
        .where(Email.category != None)
        .where(Email.timestamp >= cutoff)
        .group_by(Email.category)
        .order_by(func.count(Email.id).desc())
    )
    rows = result.all()

    total = sum(row[1] for row in rows)

    return {
        "period_days": days,
        "total_classified": total,
        "breakdown": [
            {
                "category": row[0].value if row[0] else "Unknown",
                "count": row[1],
                "percentage": round((row[1] / total * 100), 1) if total > 0 else 0,
            }
            for row in rows
        ]
    }


@router.get("/analytics/at-risk-accounts")
async def get_at_risk_accounts(
    db: AsyncSession = Depends(get_db)
):
    """
    Senders with deteriorating sentiment or unresolved threads over 48h.
    Used in the analytics dashboard at-risk panel.
    """
    cutoff_48h = datetime.now(timezone.utc) - timedelta(hours=48)

    # Unresolved threads older than 48h
    result = await db.execute(
        select(Thread, Contact)
        .join(Contact, Thread.sender_email == Contact.email)
        .where(Thread.status == "Open")
        .where(Thread.last_updated_at < cutoff_48h)
        .order_by(Thread.last_updated_at)
    )
    stale_threads = result.all()

    at_risk = []
    for thread, contact in stale_threads:
        at_risk.append({
            "sender": contact.email,
            "thread_id": thread.thread_id,
            "subject": thread.subject,
            "last_activity": str(thread.last_updated_at),
            "hours_since_activity": round(
                (datetime.now(timezone.utc) - thread.last_updated_at).total_seconds() / 3600, 1
            ),
            "risk_reason": "Unresolved thread > 48h",
            "churn_risk_score": contact.churn_risk_score,
            "account_value": contact.account_value,
        })

    return {
        "total_at_risk": len(at_risk),
        "accounts": at_risk,
    }