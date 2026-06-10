import json
import os
from typing import Optional
from groq import Groq
from app.rag.pipeline import search_knowledge_base

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CLASSIFICATION_PROMPT = """You are an AI email triage assistant for a B2B SaaS company.
Your job is to analyse an incoming email (with full thread history) and classify it.

You must return ONLY a valid JSON object — no explanation, no markdown, no extra text.

## Email to classify:
Sender: {sender}
Subject: {subject}
Body: {body}

## Full thread history (chronological):
{thread_history}

## Relevant knowledge base context:
{rag_context}

## Heuristic flags already detected:
{heuristic_flags}

## Classification rules:
- If is_security_threat=true: category=Legal or Compliance, urgency=Critical, requires_human=true, NEVER suggest auto-reply
- If is_gdpr=true: category=Compliance, urgency=High, requires_human=true, escalation_reason must mention 30-day statutory window
- If is_legal=true: category=Legal, urgency=Critical, requires_human=true, NEVER suggest auto-reply
- If is_spam=true: category=Spam, urgency=Low, requires_human=false
- If confidence < 0.70: requires_human=true (flag for human review)
- Critical urgency emails must NEVER have suggested_reply — always escalate
- suggested_reply should cite which policy document informed it

## Required JSON output:
{{
  "category": "Complaint|Inquiry|Bug Report|Feature Request|Compliance|Legal|Billing|Spam|Internal|Other",
  "sentiment": "Positive|Neutral|Negative|Mixed",
  "sentiment_score": <float -1.0 to 1.0>,
  "urgency": "Critical|High|Medium|Low",
  "requires_human": <boolean>,
  "escalation_reason": "<string if requires_human=true, else null>",
  "suggested_reply": "<string if requires_human=false and not Critical, else null>",
  "confidence": <float 0.0 to 1.0>,
  "detected_entities": {{
    "order_ids": [],
    "ticket_ids": [],
    "monetary_amounts": [],
    "deadlines": [],
    "products_mentioned": []
  }}
}}"""


def build_thread_history(thread_emails: list) -> str:
    """Format thread emails into readable history string."""
    if not thread_emails:
        return "No prior thread history."

    lines = []
    for email in thread_emails:
        lines.append(
            f"[{email.get('timestamp', 'unknown time')}] "
            f"FROM: {email.get('sender', 'unknown')}\n"
            f"SUBJECT: {email.get('subject', '(no subject)')}\n"
            f"BODY: {email.get('body', '(empty)')}\n"
            f"---"
        )
    return "\n".join(lines)


def build_rag_context(chunks: list) -> str:
    """Format RAG chunks into context string with source citations."""
    if not chunks:
        return "No relevant knowledge base context found."

    lines = []
    for chunk in chunks:
        lines.append(
            f"[SOURCE: {chunk['source_doc']} | similarity: {chunk['similarity_score']}]\n"
            f"{chunk['text']}\n"
        )
    return "\n".join(lines)


def classify_email(
    sender: str,
    subject: Optional[str],
    body: Optional[str],
    thread_emails: list,
    heuristic_flags: dict,
) -> dict:
    """
    Layer 2 — LLM classification engine.
    Takes email + thread history + RAG context → returns structured classification.
    """

    # --- Build RAG query from email content ---
    rag_query = f"{subject or ''} {body or ''}".strip()
    rag_chunks = search_knowledge_base(rag_query, top_k=3)

    # --- Format inputs ---
    thread_history = build_thread_history(thread_emails)
    rag_context = build_rag_context(rag_chunks)
    flags_str = json.dumps(heuristic_flags, indent=2)

    prompt = CLASSIFICATION_PROMPT.format(
        sender=sender,
        subject=subject or "(no subject)",
        body=body or "(empty body)",
        thread_history=thread_history,
        rag_context=rag_context,
        heuristic_flags=flags_str,
    )

    # --- Call Groq ---
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,    # low temperature for consistent structured output
            max_tokens=1000,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)

        # --- Safety overrides ---
        # These override LLM decisions for critical scenarios
        if heuristic_flags.get("is_security_threat"):
            result["urgency"] = "Critical"
            result["requires_human"] = True
            result["suggested_reply"] = None
            result["escalation_reason"] = "Security threat detected — never auto-reply"

        if heuristic_flags.get("is_legal"):
            result["urgency"] = "Critical"
            result["requires_human"] = True
            result["suggested_reply"] = None
            if not result.get("escalation_reason"):
                result["escalation_reason"] = "Legal threat — requires legal team review"

        if heuristic_flags.get("is_gdpr"):
            result["requires_human"] = True
            if not result.get("escalation_reason"):
                result["escalation_reason"] = "GDPR request — 30-day statutory window applies"

        # Flag low confidence for human review
        if result.get("confidence", 1.0) < 0.70:
            result["requires_human"] = True
            if not result.get("escalation_reason"):
                result["escalation_reason"] = f"Low confidence score ({result.get('confidence')}) — flagged for human review"

        # Attach RAG sources used
        result["rag_sources"] = [c["source_doc"] for c in rag_chunks]
        # Fix contradiction: requires_human=true needs an escalation_reason
        if result.get("requires_human") and not result.get("escalation_reason"):
            result["escalation_reason"] = "Flagged for human review"

        # Deduplicate RAG sources
        result["rag_sources"] = list(dict.fromkeys(result["rag_sources"]))

        # If requires_human, clear suggested_reply
        if result.get("requires_human"):
            result["suggested_reply"] = None
            
        return result

    except json.JSONDecodeError as e:
        # Fallback if LLM returns malformed JSON
        return {
            "category": "Other",
            "sentiment": "Neutral",
            "sentiment_score": 0.0,
            "urgency": "Medium",
            "requires_human": True,
            "escalation_reason": f"Classification failed — JSON parse error: {str(e)}",
            "suggested_reply": None,
            "confidence": 0.0,
            "detected_entities": {
                "order_ids": [], "ticket_ids": [],
                "monetary_amounts": [], "deadlines": [],
                "products_mentioned": []
            },
            "rag_sources": []
        }

    except Exception as e:
        return {
            "category": "Other",
            "sentiment": "Neutral",
            "sentiment_score": 0.0,
            "urgency": "Medium",
            "requires_human": True,
            "escalation_reason": f"Classification error: {str(e)}",
            "suggested_reply": None,
            "confidence": 0.0,
            "detected_entities": {
                "order_ids": [], "ticket_ids": [],
                "monetary_amounts": [], "deadlines": [],
                "products_mentioned": []
            },
            "rag_sources": []
        }