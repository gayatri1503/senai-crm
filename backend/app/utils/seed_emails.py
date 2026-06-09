import asyncio
import json
import httpx

DATASET_PATH = "email-data-advanced.json"
API_URL = "http://localhost:8000/api/ingest"


async def seed():
    with open(DATASET_PATH, "r") as f:
        emails = json.load(f)

    print(f"Seeding {len(emails)} emails...\n")

    async with httpx.AsyncClient() as client:
        success, duplicates, failed = 0, 0, 0

        for email in emails:
            payload = {
                "message_id": email["message_id"],
                "sender": email["sender"],
                "subject": email.get("subject"),
                "body": email.get("body"),
                "timestamp": email["timestamp"],
                "thread_id": email["thread_id"],
            }

            try:
                response = await client.post(API_URL, json=payload, timeout=10.0)
                data = response.json()

                if data.get("is_duplicate"):
                    duplicates += 1
                    print(f"  DUPLICATE  {email['message_id']}")
                else:
                    success += 1
                    flags = data.get("flags", {})
                    active_flags = [k for k, v in flags.items() if v]
                    flag_str = f" [{', '.join(active_flags)}]" if active_flags else ""
                    print(f"  OK  {email['message_id']} | {email['sender'][:40]}{flag_str}")

            except Exception as e:
                failed += 1
                print(f"  FAILED  {email['message_id']} — {e}")

    print(f"\n--- Done ---")
    print(f"  Ingested:   {success}")
    print(f"  Duplicates: {duplicates}")
    print(f"  Failed:     {failed}")


if __name__ == "__main__":
    asyncio.run(seed())