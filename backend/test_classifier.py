from dotenv import load_dotenv
load_dotenv()

from app.intelligence.classifier import classify_email
import json

# Test 1 — Ransomware (must NEVER get suggested_reply)
print("=== Ransomware Test ===")
result = classify_email(
    sender="hacker@anon-collective.net",
    subject="We have your data - Pay Now",
    body="We have exfiltrated 50,000 customer records. Send 2 BTC within 48 hours or we publish the data.",
    thread_emails=[],
    heuristic_flags={
        "is_spam_heuristic": False,
        "is_internal": False,
        "is_security_threat": True,
        "is_gdpr": False,
        "is_legal": False,
        "is_urgent": True,
    }
)
print(json.dumps(result, indent=2))

# Test 2 — GDPR request (must flag legal, mention 30-day window)
print("\n=== GDPR Test ===")
result = classify_email(
    sender="marcus.del@fintech-startup.co",
    subject="Data Export: GDPR Right to Portability Request",
    body="Under GDPR Article 20, I am formally requesting a complete export of all personal data your platform holds about me. Please provide this within the statutory 30-day window.",
    thread_emails=[],
    heuristic_flags={
        "is_spam_heuristic": False,
        "is_internal": False,
        "is_security_threat": False,
        "is_gdpr": True,
        "is_legal": False,
        "is_urgent": False,
    }
)
print(json.dumps(result, indent=2))