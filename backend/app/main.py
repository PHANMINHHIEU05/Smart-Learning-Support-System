from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.db.session import async_session_factory
from app.db.schema_compat import apply_runtime_schema_compatibility
from app.db.session import engine
from app.routers import ai_events, alerts, analytics, blocks, engagement, internal_vocabulary, monitoring, sessions, tasks, user_settings
from app.routers.monitoring import cleanup_all_monitoring_processes
from app.services.daily_analytics_service import backfill_daily_analytics, backfill_focus_heatmap_analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown events."""
    setup_logging()
    await apply_runtime_schema_compatibility(engine)
    async with async_session_factory() as db:
        daily_count = int((await db.execute(text("SELECT COUNT(*) FROM daily_analytics"))).scalar_one() or 0)
        heatmap_count = int((await db.execute(text("SELECT COUNT(*) FROM daily_focus_heatmap"))).scalar_one() or 0)
        needs_commit = False
        if daily_count == 0:
            await backfill_daily_analytics(db)
            needs_commit = True
        if heatmap_count == 0:
            await backfill_focus_heatmap_analytics(db)
            needs_commit = True
        if needs_commit:
            await db.commit()
    yield
    # Shutdown: đóng tất cả connections + dừng các monitoring subprocess
    cleanup_all_monitoring_processes()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Exception Handlers ──
register_exception_handlers(app)

# ── Routers ──
app.include_router(tasks.router)
app.include_router(sessions.router)
app.include_router(blocks.router)
app.include_router(ai_events.router)
app.include_router(alerts.router)
app.include_router(analytics.router)
app.include_router(engagement.router)
app.include_router(user_settings.router)
app.include_router(monitoring.router)
app.include_router(internal_vocabulary.router)


# ── Health Check ──
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
