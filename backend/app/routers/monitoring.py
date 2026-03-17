"""
Monitoring controller — start/stop the Python camera-monitoring subprocess
for the currently authenticated user.

The subprocess is the `frontend/src/features/monitoring/main.py` script.
It receives the user JWT token and the active study-session ID via environment
variables so it can push AI events to the backend automatically.

Extended with:
- Explicit status contract: idle | starting | active | degraded | stopped
- Runtime mode switching: external_camera / in_web_widget / alerts_only
- Session-scoped in-memory alert acknowledgements
- Read-only severity category defaults in status payload
"""
from __future__ import annotations

import os
import signal
import subprocess
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.user_setting import UserSettingUpdate
from app.services.user_settings_service import get_or_create_settings, update_settings

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])

# ── In-memory registries ──────────────────────────────────────────────────────
# user_id → subprocess.Popen  (single-process dev deployment; replace with
# Redis/DB for multi-worker prod)
_processes: dict[str, subprocess.Popen[bytes]] = {}

# user_id → currently active monitoring mode
_active_modes: dict[str, str] = {}

# user_id → alert_ids acknowledged in the current monitoring session
_acked_alerts: dict[str, set[str]] = {}

# ── Constants ─────────────────────────────────────────────────────────────────

# Read-only metadata: which AI-event types belong to each severity tier.
# Returned as part of every status response so the frontend never hard-codes
# these mappings.
_SEVERITY_DEFAULTS: dict[str, list[str]] = {
    "critical": ["microsleep", "absent_away", "severe_distraction"],
    "medium":   ["drowsiness", "phone_detected", "posture_deviation"],
    "soft":     ["focus_low"],
}

# Absolute path to the monitoring script directory
_MONITORING_DIR = (
    Path(__file__).resolve().parents[3]  # workspace root
    / "frontend" / "src" / "features" / "monitoring"
)
_MONITORING_PYTHON = _MONITORING_DIR / "venv" / "bin" / "python"
_MONITORING_SCRIPT = _MONITORING_DIR / "main.py"

# ── Schemas ───────────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    session_id: str
    show_display: bool = True  # True = open OpenCV window


class DegradedReason(BaseModel):
    code: str
    message: str
    recoverable: bool
    fallback_mode: str


class MonitoringStatusResponse(BaseModel):
    status: Literal["idle", "starting", "active", "degraded", "stopped"]
    active_mode: str | None = None
    pid: int | None = None
    degraded_reason: DegradedReason | None = None
    severity_defaults: dict[str, list[str]] = Field(
        default_factory=lambda: _SEVERITY_DEFAULTS
    )


class ModeSwitchRequest(BaseModel):
    mode: str = Field(
        ...,
        pattern=r"^(external_camera|in_web_widget|alerts_only)$",
        description="One of: external_camera, in_web_widget, alerts_only",
    )


class ModeSwitchResponse(BaseModel):
    requested_mode: str
    applied_mode: str
    status: Literal["idle", "starting", "active", "degraded", "stopped"]
    degraded_reason: DegradedReason | None = None
    persisted: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _token_from_request(request: Request) -> str:
    """Extract raw Bearer token from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return ""


def _compute_status(
    key: str,
) -> tuple[Literal["idle", "starting", "active", "degraded", "stopped"], int | None]:
    """Derive status from the _processes registry."""
    proc = _processes.get(key)
    if proc is None:
        return "idle", None
    if proc.poll() is None:
        return "active", proc.pid
    # Process exited on its own — clean up
    del _processes[key]
    return "stopped", None


def _kill_user_process(key: str) -> None:
    proc = _processes.pop(key, None)
    if proc is None:
        return
    if proc.poll() is None:
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        except ProcessLookupError:
            pass


def cleanup_all_monitoring_processes() -> None:
    """Called on server shutdown to avoid orphaned camera processes."""
    for key in list(_processes.keys()):
        _kill_user_process(key)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start", response_model=MonitoringStatusResponse)
async def start_monitoring(
    body: StartRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MonitoringStatusResponse:
    key = str(user_id)

    # Kill any existing process and reset session-scoped ack registry
    _kill_user_process(key)
    _acked_alerts.pop(key, None)

    if not _MONITORING_PYTHON.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Monitoring venv not found. "
                f"Run: cd {_MONITORING_DIR} && python -m venv venv && "
                "pip install -r requirements.txt"
            ),
        )

    # Resolve preferred mode from persisted user settings
    settings = await get_or_create_settings(db, user_id)
    mode = settings.monitoring_mode or "external_camera"

    env = {
        **os.environ,
        "MONITORING_JWT_TOKEN": _token_from_request(request),
        "MONITORING_SESSION_ID": body.session_id,
        "MONITORING_API_BASE_URL": "http://localhost:8000",
    }

    cmd = [str(_MONITORING_PYTHON), str(_MONITORING_SCRIPT)]
    if not body.show_display:
        cmd.append("--no-display")

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(_MONITORING_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {exc}")

    _processes[key] = proc
    _active_modes[key] = mode
    return MonitoringStatusResponse(
        status="active",
        active_mode=mode,
        pid=proc.pid,
        severity_defaults=_SEVERITY_DEFAULTS,
    )


@router.post("/stop", response_model=MonitoringStatusResponse)
async def stop_monitoring(
    user_id: uuid.UUID = Depends(get_current_user),
) -> MonitoringStatusResponse:
    key = str(user_id)
    _kill_user_process(key)
    _active_modes.pop(key, None)
    return MonitoringStatusResponse(
        status="stopped",
        severity_defaults=_SEVERITY_DEFAULTS,
    )


@router.get("/status", response_model=MonitoringStatusResponse)
async def monitoring_status(
    user_id: uuid.UUID = Depends(get_current_user),
) -> MonitoringStatusResponse:
    key = str(user_id)
    status, pid = _compute_status(key)
    active_mode = _active_modes.get(key) if status in ("active", "degraded") else None
    return MonitoringStatusResponse(
        status=status,
        active_mode=active_mode,
        pid=pid,
        severity_defaults=_SEVERITY_DEFAULTS,
    )


@router.post("/mode", response_model=ModeSwitchResponse)
async def switch_mode(
    body: ModeSwitchRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModeSwitchResponse:
    """
    Switch the active monitoring mode at runtime.

    - Applied immediately when a subprocess is already running.
    - Switching to `alerts_only` terminates the subprocess.
    - Requesting `external_camera` or `in_web_widget` while the subprocess is
      not running degrades to `alerts_only` and reports the reason.
    - The resolved (applied) mode is always persisted to user settings.
    """
    key = str(user_id)
    requested_mode = body.mode
    status, _pid = _compute_status(key)

    applied_mode = requested_mode
    degraded_reason: DegradedReason | None = None

    if status == "active":
        if requested_mode == "alerts_only":
            # Stop subprocess — only relay mode, no camera needed
            _kill_user_process(key)
        # For external_camera / in_web_widget the subprocess keeps running;
        # mode is metadata that the frontend uses to route its UI.
    else:
        # Subprocess is not running (idle / stopped / degraded)
        if requested_mode != "alerts_only":
            # Camera-based modes need an active session
            applied_mode = "alerts_only"
            degraded_reason = DegradedReason(
                code="PROCESS_NOT_RUNNING",
                message=(
                    f"Requested mode '{requested_mode}' requires an active monitoring session. "
                    "No subprocess is running — falling back to 'alerts_only'."
                ),
                recoverable=True,
                fallback_mode="alerts_only",
            )
            status = "degraded"

    _active_modes[key] = applied_mode

    # Persist resolved mode to user settings (non-fatal if DB write fails)
    persisted = False
    try:
        await update_settings(db, user_id, UserSettingUpdate(monitoring_mode=applied_mode))
        persisted = True
    except Exception:
        pass

    return ModeSwitchResponse(
        requested_mode=requested_mode,
        applied_mode=applied_mode,
        status=status,
        degraded_reason=degraded_reason,
        persisted=persisted,
    )


@router.post("/alerts/{alert_id}/ack", status_code=200)
async def acknowledge_alert(
    alert_id: str,
    user_id: uuid.UUID = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Acknowledge an alert for the current monitoring session.
    Acknowledgements are in-memory only and are cleared when a new session
    starts via POST /start.
    """
    key = str(user_id)
    _acked_alerts.setdefault(key, set()).add(alert_id)
    return {"alert_id": alert_id, "acknowledged": True, "scope": "session"}


@router.get("/alerts/acked", response_model=list[str])
async def get_acked_alerts(
    user_id: uuid.UUID = Depends(get_current_user),
) -> list[str]:
    """Return alert IDs acknowledged in the current session."""
    key = str(user_id)
    return list(_acked_alerts.get(key, set()))
