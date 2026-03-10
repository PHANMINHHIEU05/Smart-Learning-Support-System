from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AiEventCreate(BaseModel):
    session_id: uuid.UUID | None = None
    event_type: str = Field(..., min_length=1)
    start_at: datetime
    end_at: datetime | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: int | None = Field(default=None, ge=1, le=10)
    payload_json: Any | None = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_at is not None and self.start_at is not None:
            if self.end_at < self.start_at:
                raise ValueError("end_at phải >= start_at")
        return self


class AiEventBatchCreate(BaseModel):
    events: list[AiEventCreate] = Field(..., min_length=1, max_length=500)


class AiEventResponse(BaseModel):
    event_id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID | None = None
    event_type: str
    start_at: datetime
    end_at: datetime | None = None
    confidence: float
    severity: int | None = None
    payload_json: Any | None = None

    model_config = {"from_attributes": True}
