"""
Monitoring schemas for camera FPS telemetry and performance metrics.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class CameraTelemetry(BaseModel):
    """Camera FPS and performance metrics telemetry."""

    user_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    python_fps: int | None = None
    web_fps: float | None = None
    frame_latency_ms: int | None = None
    camera_resolution: str = "640x480"
    processing_resolution: str = "256x192"
    notes: str | None = None

    class Config:
        from_attributes = True
