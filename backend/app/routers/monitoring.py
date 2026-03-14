"""
Monitoring controller — start/stop the Python camera-monitoring subprocess
for the currently authenticated user.

The subprocess is the `frontend/src/features/monitoring/main.py` script.
It receives the user JWT token and the active study-session ID via environment
variables so it can push AI events to the backend automatically.
"""
from __future__ import annotations

import os
import signal
import subprocess
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])

# In-memory registry: user_id → subprocess.Popen
# Sufficient for single-process dev deployment; replace with Redis/DB for prod.
_processes: dict[str, subprocess.Popen[bytes]] = {}

# Absolute path to the monitoring script directory
_MONITORING_DIR = (
    Path(__file__).resolve().parents[3]  # workspace root
    / "frontend" / "src" / "features" / "monitoring"
)
_MONITORING_PYTHON = _MONITORING_DIR / "venv" / "bin" / "python"
_MONITORING_SCRIPT = _MONITORING_DIR / "main.py"


class StartRequest(BaseModel):
    session_id: str
    show_display: bool = False  # True = open OpenCV window


class MonitoringStatus(BaseModel):
    running: bool
    pid: int | None = None


def _token_from_request(request: Request) -> str:
    """Extract raw Bearer token from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return ""


@router.post("/start", response_model=MonitoringStatus)
async def start_monitoring(
    body: StartRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user),
) -> MonitoringStatus:
    key = str(user_id)

    # Kill any existing process for this user first
    _kill_user_process(key)

    if not _MONITORING_PYTHON.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Monitoring venv not found. "
                f"Run: cd {_MONITORING_DIR} && python -m venv venv && pip install -r requirements.txt"
            ),
        )

    env = {
        **os.environ,
        "MONITORING_JWT_TOKEN": _token_from_request(request),
        "MONITORING_SESSION_ID": body.session_id,
        "MONITORING_API_BASE_URL": "http://localhost:8000",
    }

    # `--no-display` skips cv2.imshow so the process can run headlessly
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
    return MonitoringStatus(running=True, pid=proc.pid)


@router.post("/stop", response_model=MonitoringStatus)
async def stop_monitoring(
    user_id: uuid.UUID = Depends(get_current_user),
) -> MonitoringStatus:
    key = str(user_id)
    _kill_user_process(key)
    return MonitoringStatus(running=False)


@router.get("/status", response_model=MonitoringStatus)
async def monitoring_status(
    user_id: uuid.UUID = Depends(get_current_user),
) -> MonitoringStatus:
    key = str(user_id)
    proc = _processes.get(key)
    if proc is None:
        return MonitoringStatus(running=False)
    # poll() returns None if still alive
    if proc.poll() is None:
        return MonitoringStatus(running=True, pid=proc.pid)
    # Process already exited — clean up
    del _processes[key]
    return MonitoringStatus(running=False)


# ── helpers ──────────────────────────────────────────────────────────────────

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
