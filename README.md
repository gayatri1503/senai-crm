# SenAI CRM — Agentic CRM Intelligence Platform

A production-grade, AI-powered CRM system that autonomously monitors a high-volume inbox, triages emails with multi-dimensional intelligence, executes agentic workflows, and surfaces real-time business insights.

## Architecture Overview

Email Input
    ↓
POST /api/ingest
    ↓
Layer 1: Heuristic Pre-filter (sub-10ms)
├── Spam detection
├── Security threat detection  
├── GDPR / Legal flag
└── Internal email routing
    ↓
Layer 2: LLM Classification (Groq + Llama 3.1)
├── Full thread history injected
├── RAG context (top-3 chunks) injected
└── Structured JSON output with safety overrides
    ↓
Layer 3: ReAct Autonomous Agent
├── get_thread_history → get_contact_profile
├── search_knowledge_base → flag_for_legal
├── escalate_to_human → draft_reply
└── Max 6 steps, dry-run mode supported
    ↓
PostgreSQL + ChromaDB
    ↓
React Frontend Dashboard

## Tech Stack

| Layer        |    Technology  | Justification |
|--------------|----------------|---------------|
| Backend      | FastAPI (async)| Native async support for background classification tasks |
| Database     | PostgreSQL     | Normalized schema + JSON columns for entities |
| Vector Store | ChromaDB       | Local, no external API dependency, sentence-transformers compatible 
| LLM          | Groq (Llama 3.1-8b-instant) | Sub-second inference, sufficient for structured classification |
| Embeddings   | sentence-transformers (all-MiniLM-L6-v2) | Free, fast, no API cost, consistent with portfolio stack |
| Agent Pattern| ReAct (Reason + Act)| Produces visible reasoning trace, industry standard |
| Frontend     | React + Vite + Recharts | Fast dev server, lightweight charting |

## Project Structure

senai-crm/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI route handlers
│   │   ├── agent/             # ReAct agent + tools
│   │   ├── intelligence/      # Heuristics + LLM classifier
│   │   ├── rag/               # ChromaDB pipeline
│   │   ├── scraper/           # Web intelligence
│   │   ├── db/                # SQLAlchemy models + database
│   │   └── utils/             # Seed scripts
│   ├── knowledge_base/        # 6 policy .md files
│   ├── alembic/               # DB migrations
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/             # Inbox, Analytics
        ├── components/        # EmailList, ThreadWorkspace
        └── utils/             # API client

## Setup Guide

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 16

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env — add GROQ_API_KEY and DATABASE_URL

# Create database
psql -U postgres -c "CREATE DATABASE senai_crm;"

# Run migrations
alembic upgrade head

# Seed knowledge base
python app/rag/pipeline.py

# Start server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Seed Email Dataset

```bash
cd backend
python app/utils/seed_emails.py      # Ingest all 60 emails
python -m app.utils.bulk_classify    # Run LLM classification on all emails
```

## API Documentation

Interactive Swagger UI available at `http://localhost:8000/docs`

Key endpoints:

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/ingest | Ingest email — validates, deduplicates, queues classification |
| GET | /dashboard/stats | Mission control counts |
| GET | /threads/{email} | Full thread history with agent logs |
| POST | /agent/dry-run/{id} | Run agent in planning mode |
| POST | /agent/run/{id} | Execute agent with tool calls |
| GET | /rag/search?q=... | Debug RAG retrieval |
| GET | /analytics/sentiment-trend | Time-series sentiment per sender |
| GET | /intelligence/reputation | Public sentiment scrape |

## AI System Design Decisions

### Conflicting Signal Handling
Some emails contain mixed signals (e.g. "I love the product but want a refund"). Resolution strategy:
1. LLM assigns a confidence score — below 0.70 auto-flags for human review
2. Safety overrides always win over LLM decisions (security threats, legal flags)
3. The `escalation_reason` field documents why the conflict was resolved as it was

### RAG Chunking Strategy
Documents are split by `##` section headings first, then by token count (400 tokens, 50-token overlap). This keeps policy sections intact as retrievable units — "Non-Profit Discount" retrieves as one chunk, not split across two.

### Agent Max Steps
Set to 6 per the assessment requirement. If unresolved after 6 tool calls, the agent automatically escalates to human with a reasoning summary. This prevents infinite loops while ensuring complex cases still get human attention.

### Safety Overrides
The LLM classification result is post-processed with hard overrides:
- `is_security_threat=true` → `urgency=Critical`, `suggested_reply=null`, never auto-reply
- `is_legal=true` → `urgency=Critical`, `suggested_reply=null`, never auto-reply
- `is_gdpr=true` → `requires_human=true`, 30-day window in escalation_reason
- `confidence < 0.70` → `requires_human=true`
- `requires_human=true` → `suggested_reply=null` (always cleared)

These overrides fire regardless of what the LLM returns, preventing the automatic disqualifier scenarios.

## Special Scenario Handling

| Scenario | Detection | Action |
|---|---|---|
| Ransomware (msg_038) | `is_security_threat` heuristic | Critical urgency, no auto-reply, security queue |
| GDPR request (msg_052) | `is_gdpr` heuristic | Compliance category, flag_for_legal, 30-day window |
| Cease & desist (msg_020) | `is_legal` heuristic | Critical urgency, legal team routing, no auto-reply |
| Karen churn (msg_033) | 3 consecutive negative emails | Deterioration alert, web intelligence triggered |
| Bob legal escalation (msg_060) | Agent ReAct loop | Thread history → SLA policy → flag_for_legal → escalate |
| Alice pro-rata (msg_041) | Full thread context in LLM | Reads 4 prior emails, retrieves pricing_policy.md |

## Known Limitations

- Web scraping of G2 and Trustpilot is blocked by their robots.txt — graceful degradation implemented, returns structured error
- Sentiment scores from Llama 3.1-8b tend to cluster at ±0.8 — a larger model would produce more granular scores
- The ReAct agent occasionally outputs multiple actions in one step despite prompt constraints — parsing handles this by extracting the first valid action
- No real-time WebSocket streaming implemented — frontend polls on page load

## Trade-off Analysis

**ChromaDB vs pgvector** — Chose ChromaDB for simplicity and zero configuration. pgvector would reduce infrastructure complexity (one database instead of two) but requires PostgreSQL extension setup. For a demo system ChromaDB is the right call.

**Groq vs OpenAI** — Groq's Llama 3.1-8b-instant provides sub-second inference at zero cost during development. GPT-4o would produce higher quality structured output but adds API cost and latency. The safety override layer compensates for any LLM quality gaps on critical scenarios.

**Background classification vs synchronous** — Classification runs as a FastAPI background task so the ingest endpoint returns immediately (fast for the streaming simulation). Trade-off: the email appears in the inbox briefly without classification data. Acceptable for this use case.