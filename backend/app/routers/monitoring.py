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
import tempfile
import uuid
import json
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.user_setting import UserSettingUpdate
from app.services.user_settings_service import get_or_create_settings, update_settings
from app.services.monitoring_orchestrator_service import (
    MonitoringOrchestratorService,
    InterventionStateResponse,
)
from app.schemas.monitoring import CameraTelemetry
from app.services import telemetry_service

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])

# ── In-memory registries ──────────────────────────────────────────────────────
# user_id → subprocess.Popen  (single-process dev deployment; replace with
# Redis/DB for multi-worker prod)
_processes: dict[str, subprocess.Popen[bytes]] = {}

# user_id → currently active monitoring mode
_active_modes: dict[str, str] = {}

# user_id → alert_ids acknowledged in the current monitoring session
_acked_alerts: dict[str, set[str]] = {}

# user_id -> snapshot jpeg path written by the monitoring subprocess
_snapshot_files: dict[str, Path] = {}

# user_id -> json metrics path written by the monitoring subprocess
_metrics_files: dict[str, Path] = {}

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
        snapshot = _snapshot_files.pop(key, None)
        metrics = _metrics_files.pop(key, None)
        if snapshot and snapshot.exists():
            snapshot.unlink(missing_ok=True)
        if metrics and metrics.exists():
            metrics.unlink(missing_ok=True)
        return
    try:
        if proc.poll() is None:
            try:
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            except ProcessLookupError:
                pass
    finally:
        snapshot = _snapshot_files.pop(key, None)
        metrics = _metrics_files.pop(key, None)
        if snapshot and snapshot.exists():
            snapshot.unlink(missing_ok=True)
        if metrics and metrics.exists():
            metrics.unlink(missing_ok=True)


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
    snapshot_dir = Path(tempfile.gettempdir()) / "smart-learning-monitoring"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{key}.jpg"
    metrics_path = snapshot_dir / f"{key}.json"
    snapshot_path.unlink(missing_ok=True)
    metrics_path.unlink(missing_ok=True)

    env = {
        **os.environ,
        "MONITORING_JWT_TOKEN": _token_from_request(request),
        "MONITORING_SESSION_ID": body.session_id,
        "MONITORING_API_BASE_URL": "http://localhost:8000",
        "MONITORING_SNAPSHOT_PATH": str(snapshot_path),
        "MONITORING_METRICS_PATH": str(metrics_path),
        "MONITORING_METRICS_INTERVAL": "0.50",
        "MONITORING_SNAPSHOT_INTERVAL": "0.10",
        "MONITORING_SNAPSHOT_JPEG_QUALITY": "72",
        "MONITORING_BATCH_INTERVAL": "5",
        "MONITORING_RETRY_INTERVAL": "15",
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
    _snapshot_files[key] = snapshot_path
    _metrics_files[key] = metrics_path
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


@router.get("/snapshot")
async def get_monitoring_snapshot(
    user_id: uuid.UUID = Depends(get_current_user),
) -> Response:
    key = str(user_id)
    snapshot_path = _snapshot_files.get(key)
    metrics_path = _metrics_files.get(key)
    if snapshot_path is None or not snapshot_path.exists():
      raise HTTPException(status_code=404, detail="Monitoring snapshot not available")

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
    }

    if metrics_path is not None and metrics_path.exists():
        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8"))
            headers["X-Python-Fps-Main"] = str(payload.get("main_fps", 0))
            headers["X-Python-Fps-Camera"] = str(payload.get("camera_fps", 0))
            headers["X-Python-Fps-Ai"] = str(payload.get("ai_fps", 0))
        except Exception:
            pass

    return Response(
        content=snapshot_path.read_bytes(),
        media_type="image/jpeg",
        headers=headers,
    )


@router.get("/interventions/{session_id}", response_model=InterventionStateResponse)
async def get_intervention_state(
    session_id: str,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterventionStateResponse:
    """
    Get current intervention state for timer UI real-time polling.

    Returns escalation level (none/warning/paused), pause reason, and countdown
    state for the active study session.

    Used by timer UI to:
    - Display warning color when distraction threshold nearing (10s+)
    - Show pause overlay when session auto-paused
    - Show resume countdown when user returns after leave-seat
    """
    orchestrator = MonitoringOrchestratorService()
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    return await orchestrator.get_live_intervention_state(
        db=db,
        user_id=user_id,
        session_id=session_uuid,
    )


# ── Telemetry Endpoints ───────────────────────────────────────────────────────


@router.post("/telemetry")
async def post_telemetry(
    body: dict[str, Any],
    current_user: uuid.UUID = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Receive camera FPS telemetry metrics from frontend monitoring module.

    Expected body:
    {
        "python_fps": int | null,
        "web_fps": float | null,
        "frame_latency_ms": int | null,
        "camera_resolution": str (default: "640x480"),
        "processing_resolution": str (default: "256x192"),
        "notes": str | null
    }
    """
    telemetry = CameraTelemetry(
        user_id=current_user,
        python_fps=body.get("python_fps"),
        web_fps=body.get("web_fps"),
        frame_latency_ms=body.get("frame_latency_ms"),
        camera_resolution=body.get("camera_resolution", "640x480"),
        processing_resolution=body.get("processing_resolution", "256x192"),
        notes=body.get("notes"),
    )
    await telemetry_service.store_telemetry(telemetry)
    return {"status": "ok", "timestamp": telemetry.timestamp}


@router.get("/telemetry", response_model=CameraTelemetry)
async def get_telemetry(
    current_user: uuid.UUID = Depends(get_current_user),
) -> CameraTelemetry:
    """Get latest camera telemetry metrics for current user."""
    latest = await telemetry_service.get_latest_telemetry(current_user)
    if not latest:
        raise HTTPException(
            status_code=404, detail="No telemetry data available"
        )
    return latest


