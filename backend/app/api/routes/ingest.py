from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.db.database import get_db
from app.db.models import (
    Contact, Thread, Email, EmailStatus,
    EmailCategory, Sentiment, Urgency
)
from app.api.schemas import EmailIngestRequest, EmailIngestResponse
from app.intelligence.heuristics import run_heuristics
from app.intelligence.classifier import classify_email

router = APIRouter()


@router.post("/ingest", response_model=EmailIngestResponse)
async def ingest_email(
    payload: EmailIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # --- Step 1: Deduplication ---
    existing = await db.execute(
        select(Email).where(Email.message_id == payload.message_id)
    )
    existing_email = existing.scalar_one_or_none()

    if existing_email:
        return EmailIngestResponse(
            job_id=str(existing_email.id),
            message_id=existing_email.message_id,
            status="duplicate",
            is_duplicate=True,
            thread_id=existing_email.thread_id,
            initial_priority_score=existing_email.initial_priority_score or 0.0,
            flags={}
        )

    # --- Step 2: Heuristics ---
    flags = run_heuristics(
        sender=payload.sender,
        subject=payload.subject,
        body=payload.body,
        thread_id=payload.thread_id
    )

    # --- Step 3: Upsert contact ---
    contact = await _get_or_create_contact(db, payload.sender)

    # --- Step 4: Upsert thread ---
    thread = await _get_or_create_thread(
        db, payload.thread_id, payload.subject, payload.sender
    )

    # --- Step 5: Parse timestamp ---
    timestamp = datetime.fromisoformat(
        payload.timestamp.replace("Z", "+00:00")
    )

    # --- Step 6: Store email ---
    email = Email(
        thread_id=payload.thread_id,
        message_id=payload.message_id,
        sender=payload.sender,
        subject=payload.subject,
        body=payload.body,
        timestamp=timestamp,
        initial_priority_score=flags["initial_priority_score"],
        is_spam_heuristic=flags["is_spam_heuristic"],
        is_internal=flags["is_internal"],
        is_security_threat=flags["is_security_threat"],
        status=EmailStatus.processing,
    )
    db.add(email)

    contact.last_contact_at = datetime.now(timezone.utc)
    thread.last_updated_at = datetime.now(timezone.utc)

    await db.flush()
    email_id = email.id
    job_id = str(uuid.uuid4())

    # --- Step 7: Background classification ---
    # Skip LLM for spam, internal, and system emails
    should_classify = not (
        flags["is_spam_heuristic"] or
        flags["is_internal"] or
        flags.get("is_system")
    )

    if should_classify:
        background_tasks.add_task(
            run_classification,
            email_id=email_id,
            sender=payload.sender,
            subject=payload.subject,
            body=payload.body,
            thread_id=payload.thread_id,
            heuristic_flags=flags,
        )

    return EmailIngestResponse(
        job_id=job_id,
        message_id=payload.message_id,
        status="received",
        is_duplicate=False,
        thread_id=payload.thread_id,
        initial_priority_score=flags["initial_priority_score"],
        flags={
            "is_spam": flags["is_spam_heuristic"],
            "is_internal": flags["is_internal"],
            "is_security_threat": flags["is_security_threat"],
            "is_gdpr": flags["is_gdpr"],
            "is_legal": flags["is_legal"],
            "is_urgent": flags["is_urgent"],
        }
    )


async def run_classification(
    email_id: int,
    sender: str,
    subject: str,
    body: str,
    thread_id: str,
    heuristic_flags: dict,
):
    """
    Background task — runs LLM classification after email is stored.
    Fetches thread history first so the LLM has full context.
    """
    from app.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Fetch full thread history for context
            result = await db.execute(
                select(Email)
                .where(Email.thread_id == thread_id)
                .where(Email.id != email_id)
                .order_by(Email.timestamp)
            )
            prior_emails = result.scalars().all()

            thread_emails = [
                {
                    "timestamp": str(e.timestamp),
                    "sender": e.sender,
                    "subject": e.subject,
                    "body": e.body,
                }
                for e in prior_emails
            ]

            # Run classification
            classification = classify_email(
                sender=sender,
                subject=subject,
                body=body,
                thread_emails=thread_emails,
                heuristic_flags=heuristic_flags,
            )

            # Map string values to enums safely
            category_map = {
                "Complaint": EmailCategory.complaint,
                "Inquiry": EmailCategory.inquiry,
                "Bug Report": EmailCategory.bug_report,
                "Feature Request": EmailCategory.feature_request,
                "Compliance": EmailCategory.compliance,
                "Legal": EmailCategory.legal,
                "Billing": EmailCategory.billing,
                "Spam": EmailCategory.spam,
                "Internal": EmailCategory.internal,
                "Other": EmailCategory.other,
            }
            sentiment_map = {
                "Positive": Sentiment.positive,
                "Neutral": Sentiment.neutral,
                "Negative": Sentiment.negative,
                "Mixed": Sentiment.mixed,
            }
            urgency_map = {
                "Critical": Urgency.critical,
                "High": Urgency.high,
                "Medium": Urgency.medium,
                "Low": Urgency.low,
            }

            # Update email record
            email_result = await db.execute(
                select(Email).where(Email.id == email_id)
            )
            email = email_result.scalar_one_or_none()

            if email:
                email.category = category_map.get(
                    classification.get("category"), EmailCategory.other
                )
                email.sentiment = sentiment_map.get(
                    classification.get("sentiment"), Sentiment.neutral
                )
                email.sentiment_score = classification.get("sentiment_score")
                email.urgency = urgency_map.get(
                    classification.get("urgency"), Urgency.medium
                )
                email.requires_human = classification.get("requires_human", True)
                email.escalation_reason = classification.get("escalation_reason")
                email.suggested_reply = classification.get("suggested_reply")
                email.confidence = classification.get("confidence")
                email.raw_entities = classification.get("detected_entities", {})
                email.status = EmailStatus.escalated if classification.get(
                    "requires_human"
                ) else EmailStatus.replied

                await db.commit()
                print(f"[Classifier] email_id={email_id} -> "
                      f"{classification.get('category')} | "
                      f"{classification.get('urgency')} | "
                      f"human={classification.get('requires_human')}")

        except Exception as e:
            print(f"[Classifier ERROR] email_id={email_id}: {e}")
            await db.rollback()


# --- Helpers ---

async def _get_or_create_contact(db: AsyncSession, email: str) -> Contact:
    result = await db.execute(
        select(Contact).where(Contact.email == email)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        contact = Contact(email=email)
        db.add(contact)
        await db.flush()
    return contact


async def _get_or_create_thread(
    db: AsyncSession,
    thread_id: str,
    subject: str,
    sender_email: str
) -> Thread:
    result = await db.execute(
        select(Thread).where(Thread.thread_id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        thread = Thread(
            thread_id=thread_id,
            subject=subject,
            sender_email=sender_email,
        )
        db.add(thread)
        await db.flush()
    return thread