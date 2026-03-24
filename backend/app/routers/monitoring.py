"""
Monitoring controller — start/stop the Python camera-monitoring subprocess
for the currently authenticated user.

The subprocess is the `frontend/src/features/monitoring/main.py` script.
It receives the user JWT token and the active study-session ID via environment
variables so it can push AI events to the backend automatically.

Extended with:
- Explicit status contract: idle | starting | active | degraded | stopped
- Runtime mode switching: browser_camera / alerts_only
- Session-scoped in-memory alert acknowledgements
- Read-only severity category defaults in status payload
"""
from __future__ import annotations

import asyncio
import datetime
import os
import signal
import subprocess
import tempfile
import uuid
import json
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, WebSocket
from fastapi import WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_user_id_from_bearer_token
from app.db.session import get_db
from app.schemas.user_setting import UserSettingUpdate
from app.services.user_settings_service import get_or_create_settings, update_settings
from app.services.monitoring_orchestrator_service import (
    MonitoringOrchestratorService,
    InterventionStateResponse,
)
from app.schemas.ai_event import AiEventCreate
from app.schemas.browser_detect import BrowserDetectResponse, PerfPayload, InterventionState
from app.services import ai_event_service
from app.services.browser_detect_service import browser_detect_service
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

# stream_ticket -> (user_id, expires_at_monotonic)
_stream_tickets: dict[str, tuple[str, float]] = {}

# ── Constants ─────────────────────────────────────────────────────────────────

# Read-only metadata: which AI-event types belong to each severity tier.
# Returned as part of every status response so the frontend never hard-codes
# these mappings.
_SEVERITY_DEFAULTS: dict[str, list[str]] = {
    "critical": ["microsleep", "absent_away", "severe_distraction"],
    "medium":   ["drowsiness", "phone_detected", "posture_deviation"],
    "soft":     ["focus_low"],
}
_STREAM_TICKET_TTL_SECONDS = 45.0


def _normalize_mode(mode: str | None) -> str:
    if mode in ("in_web_widget", "external_camera"):
        return "browser_camera"
    if mode == "alerts_only":
        return "alerts_only"
    return "browser_camera"

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
        pattern=r"^(browser_camera|alerts_only|external_camera|in_web_widget)$",
        description="One of: browser_camera, alerts_only (legacy external_camera/in_web_widget still accepted)",
    )


class ModeSwitchResponse(BaseModel):
    requested_mode: str
    applied_mode: str
    status: Literal["idle", "starting", "active", "degraded", "stopped"]
    degraded_reason: DegradedReason | None = None
    persisted: bool


class StreamTicketResponse(BaseModel):
    ticket: str
    expires_in_sec: int


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


def _load_metrics_payload(metrics_path: Path | None) -> dict[str, float]:
    default_payload = {
        "main_fps": 0.0,
        "camera_fps": 0.0,
        "ai_fps": 0.0,
    }
    if metrics_path is None or not metrics_path.exists():
        return default_payload

    try:
        raw_payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        return {
            "main_fps": float(raw_payload.get("main_fps", 0.0) or 0.0),
            "camera_fps": float(raw_payload.get("camera_fps", 0.0) or 0.0),
            "ai_fps": float(raw_payload.get("ai_fps", 0.0) or 0.0),
        }
    except Exception:
        return default_payload


def _cleanup_expired_stream_tickets() -> None:
    now = time.monotonic()
    expired = [ticket for ticket, (_, expires_at) in _stream_tickets.items() if expires_at <= now]
    for ticket in expired:
        _stream_tickets.pop(ticket, None)


def _issue_stream_ticket(user_id: uuid.UUID) -> str:
    _cleanup_expired_stream_tickets()
    ticket = uuid.uuid4().hex
    _stream_tickets[ticket] = (
        str(user_id),
        time.monotonic() + _STREAM_TICKET_TTL_SECONDS,
    )
    return ticket


def _consume_stream_ticket(ticket: str) -> uuid.UUID | None:
    _cleanup_expired_stream_tickets()
    payload = _stream_tickets.pop(ticket, None)
    if payload is None:
        return None
    user_id_str, expires_at = payload
    if expires_at <= time.monotonic():
        return None
    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        return None


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
    mode = _normalize_mode(settings.monitoring_mode)
    if settings.monitoring_mode != mode:
        await update_settings(db, user_id, UserSettingUpdate(monitoring_mode=mode))
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
        "MONITORING_API_BASE_URL": str(request.base_url).rstrip("/"),
        "MONITORING_SNAPSHOT_PATH": str(snapshot_path),
        "MONITORING_METRICS_PATH": str(metrics_path),
        "MONITORING_METRICS_INTERVAL": "0.50",
        "MONITORING_SNAPSHOT_INTERVAL": "0.08",
        "MONITORING_SNAPSHOT_JPEG_QUALITY": "68",
        "MONITORING_SNAPSHOT_MAX_WIDTH": "480",
        "MONITORING_SNAPSHOT_MAX_HEIGHT": "360",
        "MONITORING_SNAPSHOT_BRIGHTNESS_ALPHA": "1.12",
        "MONITORING_SNAPSHOT_BRIGHTNESS_BETA": "10",
        "MONITORING_BATCH_INTERVAL": "2",
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
        - Requesting `browser_camera` while the subprocess is
      not running degrades to `alerts_only` and reports the reason.
    - The resolved (applied) mode is always persisted to user settings.
    """
    key = str(user_id)
    requested_mode = _normalize_mode(body.mode)
    status, _pid = _compute_status(key)

    applied_mode = requested_mode
    degraded_reason: DegradedReason | None = None

    if status == "active":
        if requested_mode == "alerts_only":
            # Stop subprocess — only relay mode, no camera needed
            _kill_user_process(key)
        # For browser_camera the subprocess keeps running;
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
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user),
) -> Response:
    key = str(user_id)
    snapshot_path = _snapshot_files.get(key)
    metrics_path = _metrics_files.get(key)
    if snapshot_path is None or not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="Monitoring snapshot not available")

    try:
        snapshot_mtime_ns = snapshot_path.stat().st_mtime_ns
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Monitoring snapshot not available")
    except OSError:
        raise HTTPException(
            status_code=503,
            detail="Monitoring snapshot temporarily unavailable",
        )

    etag = f'W/"{snapshot_mtime_ns}"'
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "ETag": etag,
    }

    metrics_payload = _load_metrics_payload(metrics_path)
    headers["X-Python-Fps-Main"] = str(metrics_payload["main_fps"])
    headers["X-Python-Fps-Camera"] = str(metrics_payload["camera_fps"])
    headers["X-Python-Fps-Ai"] = str(metrics_payload["ai_fps"])

    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)

    try:
        payload = snapshot_path.read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Monitoring snapshot not available")
    except OSError:
        raise HTTPException(
            status_code=503,
            detail="Monitoring snapshot temporarily unavailable",
        )

    return Response(
        content=payload,
        media_type="image/jpeg",
        headers=headers,
    )


@router.websocket("/stream")
async def stream_monitoring_snapshot(websocket: WebSocket) -> None:
    ticket = websocket.query_params.get("ticket", "")
    token = websocket.query_params.get("token", "")

    user_id: uuid.UUID | None = None
    if ticket:
        user_id = _consume_stream_ticket(ticket)
        if user_id is None:
            await websocket.close(code=4401, reason="Invalid or expired stream ticket")
            return
    else:
        if not token:
            await websocket.close(code=4401, reason="Missing token")
            return

        try:
            user_id = await get_user_id_from_bearer_token(token)
        except HTTPException:
            await websocket.close(code=4401, reason="Unauthorized")
            return

    await websocket.accept()
    key = str(user_id)
    last_snapshot_mtime_ns = 0
    last_metrics_sent_at = 0.0
    waiting_announced = False

    try:
        while True:
            snapshot_path = _snapshot_files.get(key)
            metrics_path = _metrics_files.get(key)
            process_status, _ = _compute_status(key)

            if process_status != "active":
                if not waiting_announced:
                    await websocket.send_json(
                        {
                            "type": "status",
                            "ready": False,
                            "message": "Monitoring process not active",
                        }
                    )
                    waiting_announced = True
                await asyncio.sleep(0.20)
                continue

            if snapshot_path is None or not snapshot_path.exists():
                if not waiting_announced:
                    await websocket.send_json(
                        {"type": "status", "ready": False, "message": "Waiting for snapshot"}
                    )
                    waiting_announced = True
                await asyncio.sleep(0.20)
                continue

            waiting_announced = False
            snapshot_mtime_ns = snapshot_path.stat().st_mtime_ns

            if snapshot_mtime_ns != last_snapshot_mtime_ns:
                frame_bytes = await asyncio.to_thread(snapshot_path.read_bytes)
                metrics_payload = await asyncio.to_thread(_load_metrics_payload, metrics_path)
                await websocket.send_json({"type": "metrics", **metrics_payload})
                await websocket.send_bytes(frame_bytes)
                last_snapshot_mtime_ns = snapshot_mtime_ns
                last_metrics_sent_at = time.monotonic()
                continue

            now = time.monotonic()
            if now - last_metrics_sent_at >= 2.0:
                metrics_payload = await asyncio.to_thread(_load_metrics_payload, metrics_path)
                await websocket.send_json({"type": "metrics", **metrics_payload})
                last_metrics_sent_at = now

            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        return
    except Exception:
        with suppress(Exception):
            await websocket.close(code=1011, reason="Monitoring stream error")
        return


@router.post("/stream-ticket", response_model=StreamTicketResponse)
async def issue_monitoring_stream_ticket(
    user_id: uuid.UUID = Depends(get_current_user),
) -> StreamTicketResponse:
    ticket = _issue_stream_ticket(user_id)
    return StreamTicketResponse(
        ticket=ticket,
        expires_in_sec=int(_STREAM_TICKET_TTL_SECONDS),
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
    Receive camera FPS telemetry metrics for diagnostics.
    Live UI metrics are sourced from the WebSocket stream endpoint.

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
    """Get latest diagnostic telemetry metrics for current user."""
    latest = await telemetry_service.get_latest_telemetry(current_user)
    if not latest:
        raise HTTPException(
            status_code=404, detail="No telemetry data available"
        )
    return latest

_detect_last_event_at : dict[str  , float ] = {}
_DETECT_EVENT_THROTTLE_SEC = 1.0 
def _allow_detect_event_emit(user_key: str) -> bool:
    now = time.monotonic()
    last = _detect_last_event_at.get(user_key, 0.0)
    if now - last < _DETECT_EVENT_THROTTLE_SEC:
        return False
    _detect_last_event_at[user_key] = now
    return True
@router.post("/detect", response_model=BrowserDetectResponse)
async def detect_from_browser_frame(
    frame: UploadFile = File(...),
    session_id: str = Form(...),
    client_ts_ms: int | None = Form(default=None),
    frame_seq: int | None = Form(default=None),
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrowserDetectResponse:
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id") from exc

    frame_bytes = await frame.read()
    metrics = await asyncio.to_thread(browser_detect_service.analyze, frame_bytes)

    derived_event = metrics.get("derived_event")
    if metrics.get("ready") and derived_event and _allow_detect_event_emit(str(user_id)):
        now_utc = datetime.now(datetime.timezone.utc)
        try:
            await ai_event_service.create_event(
                db,
                user_id,
                AiEventCreate(
                    session_id=session_uuid,
                    event_type=str(derived_event),
                    start_at=now_utc,
                    end_at=now_utc,
                    confidence=float(metrics.get("confidence", 0.0) or 0.0),
                    payload_json={
                        "source": "browser_detect_api",
                        "client_ts_ms": client_ts_ms,
                        "frame_seq": frame_seq,
                        "focus_score": metrics.get("focus_score"),
                        **metrics.get("state_flags", {}),
                    },
                ),
            )
            await db.commit()
        except Exception:
            await db.rollback()

    # ── Direct Response Mode (No Polling) ──────────────────────────────────────
    # Fetch live intervention state directly instead of requiring separate polling call
    orchestrator = MonitoringOrchestratorService()
    intervention_state_response = await orchestrator.get_live_intervention_state(
        db=db,
        user_id=user_id,
        session_id=session_uuid,
    )
    
    intervention_state = InterventionState(
        escalation_level=intervention_state_response.escalation_level,
        pause_reason=intervention_state_response.pause_reason,
        resume_countdown_sec=intervention_state_response.resume_countdown_sec,
        last_update_ts=intervention_state_response.last_update_ts,
    )

    return BrowserDetectResponse(
        ready=bool(metrics.get("ready", False)),
        server_ts_ms=int(time.time() * 1000),
        session_id=str(session_uuid),
        frame_seq=frame_seq,
        focus_score=float(metrics.get("focus_score", 0.0) or 0.0),
        confidence=float(metrics.get("confidence", 0.0) or 0.0),
        state_flags=metrics.get("state_flags", {}),
        overlay=metrics.get("overlay", {}),
        perf=PerfPayload(
            detect_ms=int(metrics.get("detect_ms", 0) or 0),
            server_ai_fps=float(metrics.get("server_ai_fps", 0.0) or 0.0),
        ),
        derived_event=str(derived_event) if derived_event else None,
        intervention_state=intervention_state,
    )
@router.websocket("/alerts-stream")
async def monitoring_alerts_stream(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
) -> None:
    ticket = websocket.query_params.get("ticket", "")
    raw_session_id = websocket.query_params.get("session_id", "")
    user_id = _consume_stream_ticket(ticket)
    if user_id is None:
        await websocket.close(code=4401, reason="Invalid or expired stream ticket")
        return

    try:
        session_uuid = uuid.UUID(raw_session_id)
    except ValueError:
        await websocket.close(code=4400, reason="Invalid session_id")
        return

    await websocket.accept()
    last_sent_alert_id: str | None = None

    try:
        while True:
            rows = await db.execute(
                text(
                    """
                    SELECT alert_id::text, message, payload_json, fired_at::text
                    FROM alerts
                    WHERE user_id = :user_id
                    AND session_id = :session_id
                    ORDER BY fired_at DESC
                    LIMIT 1
                    """
                ),
                {"user_id": str(user_id), "session_id": str(session_uuid)},
            )
            item = rows.mappings().first()
            if item and item["alert_id"] != last_sent_alert_id:
                payload = item.get("payload_json") or {}
                await websocket.send_json(
                    {
                        "type": "alert",
                        "session_id": str(session_uuid),
                        "alert_id": item["alert_id"],
                        "severity": payload.get("severity", "medium"),
                        "event_type": payload.get("event_type"),
                        "message": item.get("message") or "Alert",
                        "created_at": item.get("fired_at"),
                    }
                )
                last_sent_alert_id = item["alert_id"]

            await asyncio.sleep(0.8)
    except WebSocketDisconnect:
        return
    except Exception:
        with suppress(Exception):
            await websocket.close(code=1011, reason="alerts-stream failure")