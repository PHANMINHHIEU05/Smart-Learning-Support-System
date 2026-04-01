"""
Browser Detect API schemas — response structures for frame analysis endpoint.
Combines detection metrics with live intervention state (direct response, not polling).
"""
from pydantic import BaseModel, Field
from typing import Any, Literal


class PerfPayload(BaseModel):
    """Performance metrics for frame detection"""
    detect_ms: int = Field(..., description="Frame detection latency in milliseconds")
    server_ai_fps: float = Field(..., description="Server AI processing FPS")


class InterventionState(BaseModel):
    """Live intervention state included directly in detect response"""
    escalation_level: Literal["none", "warning", "paused"] = Field(
        ..., description="Current intervention escalation level"
    )
    pause_reason: Literal["distraction", "leave_seat"] | None = Field(
        default=None, description="Reason for pause if escalation_level is 'paused'"
    )
    resume_countdown_sec: float | None = Field(
        default=None, description="Countdown seconds until auto-resume (if applicable)"
    )
    last_update_ts: str = Field(
        default="", description="ISO timestamp of last intervention state change"
    )


class BrowserDetectResponse(BaseModel):
    """
    Direct response from /detect endpoint.
    Includes both frame metrics AND live intervention state.
    Frontend receives everything needed — no separate polling required.
    """
    ready: bool = Field(
        ..., description="Whether AI model has initialized and is ready"
    )
    server_ts_ms: int = Field(
        ..., description="Server timestamp in milliseconds (current time)"
    )
    session_id: str = Field(..., description="Study session ID")
    frame_seq: int | None = Field(
        default=None, description="Frame sequence number from client (for debugging)"
    )
    focus_score: float = Field(
        ..., description="Focus score 0-100"
    )
    confidence: float = Field(
        ..., description="Confidence score 0-1 (normalized from focus_score)"
    )
    state_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="State flags (is_drowsy, is_bad_posture, is_distracted, is_using_phone, is_too_close, is_too_far)"
    )
    overlay: dict[str, Any] = Field(
        default_factory=dict, description="Overlay data (pose_points, labels)"
    )
    perf: PerfPayload = Field(..., description="Performance metrics")
    derived_event: str | None = Field(
        default=None, description="Derived AI event type (drowsiness, phone_detected, etc.)"
    )
    is_calibrating: bool = Field(
        default=False,
        description="Whether AI runtime is currently collecting personal baseline samples"
    )
    calibration_progress: float = Field(
        default=0.0,
        description="Calibration progress percentage (0-100)"
    )
    # ── Direct Response (No Polling) ───────────────────────────────────────────
    intervention_state: InterventionState = Field(
        ...,
        description="Live intervention state — returned directly instead of requiring separate polling"
    )


class BrowserDetectRequest(BaseModel):
    """Request metadata for detect endpoint (for documentation)"""
    # Note: actual endpoint uses multipart form (frame, session_id, client_ts_ms, frame_seq)
    session_id: str
    client_ts_ms: int | None = None
    frame_seq: int | None = None
