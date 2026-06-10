import asyncio
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import (
    Email, EmailStatus, EmailCategory,
    Sentiment, Urgency
)
from app.intelligence.classifier import classify_email


async def bulk_classify():
    """
    Run LLM classification on all unclassified emails.
    Skips spam, internal, and already-classified emails.
    """
    async with AsyncSessionLocal() as db:
        # Get all unclassified non-spam non-internal emails
        result = await db.execute(
            select(Email)
            .where(Email.category == None)
            .where(Email.is_spam_heuristic == False)
            .where(Email.is_internal == False)
            .order_by(Email.timestamp)
        )
        emails = result.scalars().all()

        print(f"Found {len(emails)} unclassified emails\n")

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

        success = 0
        failed = 0

        for email in emails:
            try:
                # Get thread history for context
                thread_result = await db.execute(
                    select(Email)
                    .where(Email.thread_id == email.thread_id)
                    .where(Email.id != email.id)
                    .order_by(Email.timestamp)
                )
                prior_emails = thread_result.scalars().all()

                thread_emails = [
                    {
                        "timestamp": str(e.timestamp),
                        "sender": e.sender,
                        "subject": e.subject,
                        "body": e.body,
                    }
                    for e in prior_emails
                ]

                heuristic_flags = {
                    "is_spam_heuristic": email.is_spam_heuristic,
                    "is_internal": email.is_internal,
                    "is_security_threat": email.is_security_threat,
                    "is_gdpr": False,
                    "is_legal": False,
                    "is_urgent": False,
                }

                classification = classify_email(
                    sender=email.sender,
                    subject=email.subject,
                    body=email.body,
                    thread_emails=thread_emails,
                    heuristic_flags=heuristic_flags,
                )

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
                email.status = (
                    EmailStatus.escalated
                    if classification.get("requires_human")
                    else EmailStatus.replied
                )

                await db.commit()
                success += 1
                print(
                    f"  OK  {email.message_id} | "
                    f"{classification.get('category')} | "
                    f"{classification.get('urgency')} | "
                    f"score={classification.get('sentiment_score')} | "
                    f"human={classification.get('requires_human')}"
                )

            except Exception as e:
                failed += 1
                await db.rollback()
                print(f"  FAILED  {email.message_id} — {e}")

        print(f"\n--- Done ---")
        print(f"  Classified: {success}")
        print(f"  Failed:     {failed}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(bulk_classify())