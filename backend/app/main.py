"""
main.py — FastAPI application entry point.

All routers are registered here.
On startup: storage directories are created, DB tables are created, demo meeting is seeded.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import create_all_tables, get_db, AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Startup
    settings.ensure_storage_dirs()
    await create_all_tables()

    # Automatically seed the high-fidelity demo meeting
    try:
        from app.seed import seed_demo_meeting
        async with AsyncSessionLocal() as session:
            await seed_demo_meeting(session)
    except Exception as e:
        print(f"[WARN] Automatic demo meeting seeding skipped: {e}")

    yield
    # Shutdown


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="MOM for meetings — Evidence-grounded meeting intelligence system.",
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
    integrations,
    ws,
)

app.include_router(meetings.router, prefix="/api/meetings", tags=["Meetings"])
app.include_router(capture.router, prefix="/api/capture", tags=["Capture"])
app.include_router(ingestion.router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["Ingestion"])
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
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(agent_console.router, prefix="/api/agent", tags=["Agent Console"])
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])
app.include_router(ws.router, prefix="/api/ws", tags=["WebSocket"])


async def _get_system_health(db: AsyncSession) -> dict:
    """Build structured health status for all subcomponents."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    storage_status = "healthy"
    try:
        if not (settings.audio_storage.exists() and settings.artifact_storage.exists()):
            settings.ensure_storage_dirs()
    except Exception:
        storage_status = "degraded"

    mode = "DEMO"
    if settings.llm_provider != "stub" or settings.asr_provider != "stub":
        mode = "REAL" if not settings.debug else "DEV"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "backend": "healthy",
        "database": db_status,
        "storage": storage_status,
        "mode": mode,
        "version": settings.app_version,
        "llm": {
            "provider": str(settings.llm_provider),
            "status": "available",
        },
        "asr": {
            "provider": str(settings.asr_provider),
            "status": "available",
        },
        "diarization": {
            "provider": str(settings.diarization_provider),
            "status": "available",
        },
        "overlay": {
            "capability": "available",
            "port": settings.overlay_port,
            "hotkey": settings.overlay_hotkey,
        },
        "frontend_compatibility": {
            "api_version": settings.app_version,
            "status": "compatible",
        },
    }


@app.get("/api/health", summary="Structured system health check")
async def api_health(db: AsyncSession = Depends(get_db)) -> dict:
    return await _get_system_health(db)


@app.get("/health", summary="System health check")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    return await _get_system_health(db)
