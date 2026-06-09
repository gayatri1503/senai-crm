from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.db.database import get_db
from app.db.models import Contact, Thread, Email, EmailStatus
from app.api.schemas import EmailIngestRequest, EmailIngestResponse, ErrorResponse
from app.intelligence.heuristics import run_heuristics

router = APIRouter()


@router.post(
    "/ingest",
    response_model=EmailIngestResponse,
    responses={422: {"model": ErrorResponse}}
)
async def ingest_email(
    payload: EmailIngestRequest,
    db: AsyncSession = Depends(get_db)
):
    # --- Step 1: Deduplication check ---
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

    # --- Step 2: Run heuristic pre-filter ---
    flags = run_heuristics(
        sender=payload.sender,
        subject=payload.subject,
        body=payload.body,
        thread_id=payload.thread_id
    )

    # --- Step 3: Upsert contact ---
    contact = await _get_or_create_contact(db, payload.sender)

    # --- Step 4: Upsert thread ---
    thread = await _get_or_create_thread(db, payload.thread_id, payload.subject, payload.sender)

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
        status=EmailStatus.received,
    )
    db.add(email)

    # --- Step 7: Update contact last_contact_at ---
    contact.last_contact_at = datetime.now(timezone.utc)

    # --- Step 8: Update thread last_updated_at ---
    thread.last_updated_at = datetime.now(timezone.utc)

    await db.flush()  # get email.id without full commit

    job_id = str(uuid.uuid4())

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


# --- Helper functions ---

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