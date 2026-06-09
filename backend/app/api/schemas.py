from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


# --- Request schema (what POST /api/ingest accepts) ---

class EmailIngestRequest(BaseModel):
    message_id: str
    sender: str
    subject: Optional[str] = None
    body: Optional[str] = None
    timestamp: str
    thread_id: str

    @field_validator("message_id", "thread_id")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()

    @field_validator("body")
    @classmethod
    def sanitize_body(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # Strip pure whitespace bodies
        stripped = v.strip()
        if not stripped:
            return None
        # Truncate extremely long bodies to 10,000 chars
        if len(stripped) > 10000:
            return stripped[:10000] + "\n\n[TRUNCATED]"
        return stripped

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("Invalid timestamp format. Use ISO 8601.")
        return v


# --- Response schemas ---

class EmailIngestResponse(BaseModel):
    job_id: str
    message_id: str
    status: str
    is_duplicate: bool
    thread_id: str
    initial_priority_score: float
    flags: dict


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[dict] = None