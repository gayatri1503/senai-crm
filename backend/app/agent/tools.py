from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Email, Thread, Contact, Action, ActionType
from app.rag.pipeline import search_knowledge_base as rag_search
from datetime import datetime, timezone


# --- Tool implementations ---

async def tool_get_thread_history(
    sender_email: str,
    db: AsyncSession
) -> dict:
    """Retrieve all emails from this sender ordered by time."""
    result = await db.execute(
        select(Email)
        .where(Email.sender == sender_email)
        .order_by(Email.timestamp)
    )
    emails = result.scalars().all()

    return {
        "sender": sender_email,
        "total_emails": len(emails),
        "emails": [
            {
                "message_id": e.message_id,
                "subject": e.subject,
                "body": (e.body or "")[:500],
                "timestamp": str(e.timestamp),
                "thread_id": e.thread_id,
                "category": e.category.value if e.category else None,
                "urgency": e.urgency.value if e.urgency else None,
                "sentiment_score": e.sentiment_score,
            }
            for e in emails
        ]
    }


async def tool_get_contact_profile(
    email: str,
    db: AsyncSession
) -> dict:
    """Fetch CRM profile: VIP status, account value, churn risk."""
    result = await db.execute(
        select(Contact).where(Contact.email == email)
    )
    contact = result.scalar_one_or_none()

    if not contact:
        return {"error": f"No contact found for {email}"}

    # Count threads
    threads_result = await db.execute(
        select(Thread).where(Thread.sender_email == email)
    )
    threads = threads_result.scalars().all()

    return {
        "email": contact.email,
        "name": contact.name,
        "company": contact.company,
        "status": contact.status.value if contact.status else "Active",
        "account_value": contact.account_value,
        "churn_risk_score": contact.churn_risk_score,
        "open_threads": len([t for t in threads if t.status.value == "Open"]),
        "total_threads": len(threads),
        "last_contact_at": str(contact.last_contact_at),
    }


async def tool_search_knowledge_base(query: str) -> dict:
    """RAG search across internal policy documents."""
    chunks = rag_search(query, top_k=3)
    return {
        "query": query,
        "results": [
            {
                "source": c["source_doc"],
                "score": c["similarity_score"],
                "text": c["text"][:400],
            }
            for c in chunks
        ]
    }


async def tool_escalate_to_human(
    email_id: int,
    reason: str,
    priority: str,
    db: AsyncSession
) -> dict:
    """Route email to human with pre-filled brief."""
    result = await db.execute(
        select(Email).where(Email.id == email_id)
    )
    email = result.scalar_one_or_none()

    if not email:
        return {"error": f"Email {email_id} not found"}

    from app.db.models import EmailStatus, ThreadStatus
    email.status = EmailStatus.escalated
    email.requires_human = True
    email.escalation_reason = reason

    # Update thread status
    thread_result = await db.execute(
        select(Thread).where(Thread.thread_id == email.thread_id)
    )
    thread = thread_result.scalar_one_or_none()
    if thread:
        thread.status = ThreadStatus.escalated

    await db.flush()

    return {
        "status": "escalated",
        "email_id": email_id,
        "priority": priority,
        "reason": reason,
        "message": f"Email escalated to human with priority {priority}"
    }


async def tool_flag_for_legal(
    email_id: int,
    issue_type: str,
    db: AsyncSession
) -> dict:
    """Route legal threats to legal team with context summary."""
    result = await db.execute(
        select(Email).where(Email.id == email_id)
    )
    email = result.scalar_one_or_none()

    if not email:
        return {"error": f"Email {email_id} not found"}

    action = Action(
        email_id=email_id,
        action_type=ActionType.legal_flag,
        proposed_content=f"Legal flag: {issue_type}",
        is_approved=True,
        approved_by="agent",
        executed_at=datetime.now(timezone.utc),
    )
    db.add(action)
    await db.flush()

    return {
        "status": "flagged",
        "email_id": email_id,
        "issue_type": issue_type,
        "routed_to": "legal@ourcompany.com",
        "action_id": action.id,
    }


async def tool_create_internal_ticket(
    title: str,
    body: str,
    assignee: str,
    email_id: int,
    db: AsyncSession
) -> dict:
    """Create a support/engineering ticket."""
    action = Action(
        email_id=email_id,
        action_type=ActionType.ticket_created,
        proposed_content=f"TICKET: {title}\n\nAssignee: {assignee}\n\n{body}",
        is_approved=True,
        approved_by="agent",
        executed_at=datetime.now(timezone.utc),
    )
    db.add(action)
    await db.flush()

    return {
        "status": "created",
        "ticket_title": title,
        "assignee": assignee,
        "action_id": action.id,
    }


async def tool_draft_reply(
    context: str,
    tone: str,
    policy_refs: list,
    email_id: int,
    db: AsyncSession
) -> dict:
    """Generate a contextual reply citing specific policies."""
    import os
    from groq import Groq

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = f"""Draft a professional email reply with the following context:

Context: {context}
Tone: {tone}
Policy references to cite: {', '.join(policy_refs)}

Write only the email body — no subject line, no explanation.
Be empathetic, clear, and cite the relevant policies."""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=500,
    )

    draft = response.choices[0].message.content.strip()

    action = Action(
        email_id=email_id,
        action_type=ActionType.auto_reply,
        proposed_content=draft,
        is_approved=False,
        approved_by=None,
    )
    db.add(action)
    await db.flush()

    return {
        "status": "drafted",
        "draft": draft,
        "action_id": action.id,
        "policy_refs": policy_refs,
    }