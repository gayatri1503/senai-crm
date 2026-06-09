import re
from typing import Optional


# --- Keyword lists ---

SPAM_KEYWORDS = [
    "seo", "boost your", "front page of google", "limited offer",
    "click here to claim", "nigerian prince", "inheritance",
    "processing fee", "bank account details", "wealth transfer",
    "collab opportunity", "pure win-win", "cold outreach",
    "are you the right person", "software purchasing decisions",
    "100k followers", "dm me"
]

URGENCY_KEYWORDS = [
    "urgent", "p0", "legal", "cease and desist", "ransomware",
    "lawyer", "lawsuit", "production down", "critical", "outage",
    "losing money", "per minute", "legal action", "formal notice",
    "sla breach", "escalation", "legal team", "legal review"
]

SECURITY_KEYWORDS = [
    "ransomware", "exfiltrated", "bitcoin", "btc", "dark web",
    "suspicious login", "unauthorized access", "data breach",
    "hacked", "send 2 btc", "publish data", "anon-collective",
    "unknown location", "pyongyang", "suspicious ip"
]

GDPR_KEYWORDS = [
    "gdpr", "article 20", "data portability", "right to portability",
    "data export", "personal data export", "gdpr request",
    "data subject", "right to erasure", "article 17"
]

LEGAL_KEYWORDS = [
    "cease and desist", "trademark", "registered trademark",
    "legal action", "attorney", "counsel", "lawsuit",
    "litigation", "legal team is now involved",
    "formal correspondence", "legal review"
]

INTERNAL_DOMAINS = [
    "@internal.com", "@mycompany.com", "@company.com"
]

SYSTEM_SENDERS = [
    "noreply@", "no-reply@", "donotreply@",
    "billing@saas-platform.com", "renewals@service.com",
    "newsletter@", "support@cloudvendor.com",
    "bot@review-scraper.io", "noreply@github.com",
    "admin@platform.com"
]


def run_heuristics(
    sender: str,
    subject: Optional[str],
    body: Optional[str],
    thread_id: str
) -> dict:
    """
    Layer 1 — fast heuristic pre-filter.
    Returns flags and an initial priority score.
    Runs synchronously, must be sub-10ms.
    """
    text = _combined_text(sender, subject, body)
    text_lower = text.lower()

    is_internal = _check_internal(sender)
    is_system = _check_system_sender(sender)
    is_spam = _check_spam(text_lower) and not is_internal
    is_security_threat = _check_security(text_lower)
    is_gdpr = _check_gdpr(text_lower)
    is_legal = _check_legal(text_lower)
    is_urgent = _check_urgency(text_lower)

    priority_score = _calculate_priority(
        is_security_threat, is_legal, is_gdpr,
        is_urgent, is_spam, is_internal, is_system
    )

    return {
        "is_internal": is_internal,
        "is_system": is_system,
        "is_spam_heuristic": is_spam,
        "is_security_threat": is_security_threat,
        "is_gdpr": is_gdpr,
        "is_legal": is_legal,
        "is_urgent": is_urgent,
        "initial_priority_score": priority_score,
    }


# --- Helper functions ---

def _combined_text(sender: str, subject: Optional[str], body: Optional[str]) -> str:
    parts = [sender or "", subject or "", body or ""]
    return " ".join(parts)


def _check_internal(sender: str) -> bool:
    sender_lower = sender.lower()
    return any(domain in sender_lower for domain in INTERNAL_DOMAINS)


def _check_system_sender(sender: str) -> bool:
    sender_lower = sender.lower()
    return any(s in sender_lower for s in SYSTEM_SENDERS)


def _check_spam(text_lower: str) -> bool:
    return any(keyword in text_lower for keyword in SPAM_KEYWORDS)


def _check_security(text_lower: str) -> bool:
    return any(keyword in text_lower for keyword in SECURITY_KEYWORDS)


def _check_gdpr(text_lower: str) -> bool:
    return any(keyword in text_lower for keyword in GDPR_KEYWORDS)


def _check_legal(text_lower: str) -> bool:
    return any(keyword in text_lower for keyword in LEGAL_KEYWORDS)


def _check_urgency(text_lower: str) -> bool:
    return any(keyword in text_lower for keyword in URGENCY_KEYWORDS)


def _calculate_priority(
    is_security: bool,
    is_legal: bool,
    is_gdpr: bool,
    is_urgent: bool,
    is_spam: bool,
    is_internal: bool,
    is_system: bool
) -> float:
    """
    Priority score 0.0 to 1.0.
    Higher = needs faster attention.
    """
    if is_security:
        return 1.0
    if is_legal:
        return 0.95
    if is_gdpr:
        return 0.90
    if is_urgent:
        return 0.80
    if is_spam or is_system:
        return 0.0
    if is_internal:
        return 0.1
    return 0.5   # default for normal customer emails