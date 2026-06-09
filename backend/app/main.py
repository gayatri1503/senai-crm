from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.routes import ingest

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

# Register routers
app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])


@app.get("/")
async def root():
    return {"status": "ok", "message": "SenAI CRM is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}