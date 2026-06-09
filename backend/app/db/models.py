from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, 
    Text, Integer, ForeignKey, JSON, Enum
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


# --- Enums ---

class ContactStatus(str, enum.Enum):
    active = "Active"
    vip = "VIP"
    blocked = "Blocked"
    churned = "Churned"


class ThreadStatus(str, enum.Enum):
    open = "Open"
    resolved = "Resolved"
    escalated = "Escalated"
    ignored = "Ignored"


class EmailStatus(str, enum.Enum):
    received = "Received"
    processing = "Processing"
    replied = "Replied"
    escalated = "Escalated"
    ignored = "Ignored"


class EmailCategory(str, enum.Enum):
    complaint = "Complaint"
    inquiry = "Inquiry"
    bug_report = "Bug Report"
    feature_request = "Feature Request"
    compliance = "Compliance"
    legal = "Legal"
    billing = "Billing"
    spam = "Spam"
    internal = "Internal"
    other = "Other"


class Urgency(str, enum.Enum):
    critical = "Critical"
    high = "High"
    medium = "Medium"
    low = "Low"


class Sentiment(str, enum.Enum):
    positive = "Positive"
    neutral = "Neutral"
    negative = "Negative"
    mixed = "Mixed"


class ActionType(str, enum.Enum):
    auto_reply = "Auto-Reply"
    escalate = "Escalate"
    legal_flag = "Legal-Flag"
    ticket_created = "Ticket-Created"
    ignored = "Ignored"


# --- Tables ---

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    status = Column(Enum(ContactStatus), default=ContactStatus.active, nullable=False)
    account_value = Column(Float, default=0.0)
    churn_risk_score = Column(Float, default=0.0)  # 0.0 to 1.0
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_contact_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    threads = relationship("Thread", back_populates="contact")


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(255), unique=True, nullable=False, index=True)
    subject = Column(String(500), nullable=True)
    sender_email = Column(String(255), ForeignKey("contacts.email"), nullable=False)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status = Column(Enum(ThreadStatus), default=ThreadStatus.open, nullable=False)
    assigned_to = Column(String(255), nullable=True)

    # Relationships
    contact = relationship("Contact", back_populates="threads")
    emails = relationship("Email", back_populates="thread", order_by="Email.timestamp")


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(255), ForeignKey("threads.thread_id"), nullable=False, index=True)
    message_id = Column(String(255), unique=True, nullable=False, index=True)  # idempotency key
    sender = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    # Set by heuristic pre-filter (Layer 1)
    initial_priority_score = Column(Float, default=0.0)
    is_spam_heuristic = Column(Boolean, default=False)
    is_internal = Column(Boolean, default=False)
    is_security_threat = Column(Boolean, default=False)

    # Set by LLM classification (Layer 2)
    category = Column(Enum(EmailCategory), nullable=True)
    sentiment = Column(Enum(Sentiment), nullable=True)
    sentiment_score = Column(Float, nullable=True)   # -1.0 to +1.0
    urgency = Column(Enum(Urgency), nullable=True)
    requires_human = Column(Boolean, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    suggested_reply = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)        # 0.0 to 1.0
    raw_entities = Column(JSON, nullable=True)       # order_ids, deadlines, etc.

    status = Column(Enum(EmailStatus), default=EmailStatus.received, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    thread = relationship("Thread", back_populates="emails")
    actions = relationship("Action", back_populates="email")


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)
    agent_reasoning_log = Column(JSON, nullable=True)   # full Thought→Action→Observation trace
    action_type = Column(Enum(ActionType), nullable=False)
    proposed_content = Column(Text, nullable=True)      # draft reply text
    is_approved = Column(Boolean, default=False)
    approved_by = Column(String(255), nullable=True)    # user id or "agent"
    executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    email = relationship("Email", back_populates="actions")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_doc = Column(String(255), nullable=False, index=True)  # e.g. "refund_policy.md"
    chunk_text = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)   # stored as list of floats (we'll use ChromaDB for search)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WebIntelligenceCache(Base):
    __tablename__ = "web_intelligence_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_url = Column(String(500), nullable=False)
    target_entity = Column(String(255), nullable=False, index=True)  # company name
    scraped_data = Column(JSON, nullable=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(100), nullable=False)   # "email", "contact", "thread"
    entity_id = Column(String(255), nullable=False)
    action = Column(String(255), nullable=False)
    performed_by = Column(String(255), nullable=False)  # "agent" or user id
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    diff = Column(JSON, nullable=True)                  # what changed