from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.routes import ingest, rag, dashboard, threads, agent, analytics, intelligence

load_dotenv()

app = FastAPI(
    title="SenAI CRM",
    description="Agentic CRM Intelligence Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])
app.include_router(rag.router, prefix="", tags=["RAG"])
app.include_router(dashboard.router, prefix="", tags=["Dashboard"])
app.include_router(threads.router, prefix="", tags=["Threads"])
app.include_router(agent.router, prefix="", tags=["Agent"])
app.include_router(analytics.router, prefix="", tags=["Analytics"])
app.include_router(intelligence.router, prefix="", tags=["Intelligence"])


@app.get("/")
async def root():
    return {"status": "ok", "message": "SenAI CRM is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}