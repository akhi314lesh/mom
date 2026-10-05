"""
main.py — FastAPI application entry point.

All routers are registered here.
On startup: storage directories are created, DB tables are created.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_all_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Startup
    settings.ensure_storage_dirs()
    await create_all_tables()
    yield
    # Shutdown (nothing needed yet)


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Evidence-grounded meeting intelligence system.",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from app.api import (  # noqa: E402
    meetings,
    capture,
    ingestion,
    processing,
    transcript,
    evidence,
    review,
    actions,
    decisions,
    knowledge,
    artifacts,
    query,
    agent_console,
    contradictions,
    continuity,
    people,
    ws,
)

app.include_router(meetings.router, prefix="/api/meetings", tags=["Meetings"])
app.include_router(capture.router, prefix="/api/capture", tags=["Capture"])
app.include_router(ingestion.router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(processing.router, prefix="/api/processing", tags=["Processing"])
app.include_router(transcript.router, prefix="/api/transcript", tags=["Transcript"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["Evidence"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])
app.include_router(actions.router, prefix="/api/actions", tags=["Actions"])
app.include_router(decisions.router, prefix="/api/decisions", tags=["Decisions"])
app.include_router(contradictions.router, prefix="/api/contradictions", tags=["Contradictions"])
app.include_router(continuity.router, prefix="/api/continuity", tags=["Continuity"])
app.include_router(people.router, prefix="/api/people", tags=["People"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])
app.include_router(artifacts.router, prefix="/api/artifacts", tags=["Artifacts"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(agent_console.router, prefix="/api/agent", tags=["Agent Console"])
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])
app.include_router(ws.router, prefix="/api/ws", tags=["WebSocket"])


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": settings.app_version,
        "llm_provider": settings.llm_provider,
        "asr_provider": settings.asr_provider,
        "diarization_provider": settings.diarization_provider,
    }
