from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.db.session import engine
from app.routers import ai_events, alerts, analytics, blocks, monitoring, sessions, tasks, user_settings
from app.routers.monitoring import cleanup_all_monitoring_processes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown events."""
    setup_logging()
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
app.include_router(user_settings.router)
app.include_router(monitoring.router)


# ── Health Check ──
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
