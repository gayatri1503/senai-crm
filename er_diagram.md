# Database ER Diagram

## Entity Relationship Diagram

```mermaid
erDiagram
  contacts {
    int id PK
    string email
    string name
    string company
    string status
    float account_value
    float churn_risk_score
    datetime created_at
    datetime last_contact_at
  }
  threads {
    int id PK
    string thread_id
    string subject
    string sender_email FK
    string status
    string assigned_to
    datetime first_seen_at
    datetime last_updated_at
  }
  emails {
    int id PK
    string thread_id FK
    string message_id
    string sender
    string subject
    text body
    datetime timestamp
    float priority_score
    bool is_spam
    bool is_internal
    bool is_security_threat
    string category
    string sentiment
    float sentiment_score
    string urgency
    bool requires_human
    text escalation_reason
    text suggested_reply
    float confidence
    json raw_entities
    string status
  }
  actions {
    int id PK
    int email_id FK
    string action_type
    text proposed_content
    json agent_reasoning_log
    bool is_approved
    string approved_by
    datetime executed_at
  }
  knowledge_chunks {
    int id PK
    string source_doc
    text chunk_text
    json embedding
    datetime created_at
  }
  web_intelligence_cache {
    int id PK
    string source_url
    string target_entity
    json scraped_data
    datetime scraped_at
    datetime expires_at
  }
  audit_log {
    int id PK
    string entity_type
    string entity_id
    string action
    string performed_by
    json diff
    datetime timestamp
  }

  contacts ||--o{ threads : "has threads"
  threads ||--o{ emails : "contains"
  emails ||--o{ actions : "triggers"
```

## Relationship Notes

- One contact has many threads — Bob Jones has both `thread_bob_outage` and `thread_bob_api_limits`
- One thread has many emails — ordered by timestamp to give full conversation context to the LLM
- One email has many actions — each agent tool call (flag_for_legal, escalate_to_human, draft_reply) creates an action row
- `knowledge_chunks`, `web_intelligence_cache`, and `audit_log` are standalone — no foreign keys, support the intelligence pipeline