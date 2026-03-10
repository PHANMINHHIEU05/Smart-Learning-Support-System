from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    task_id: uuid.UUID | None = None
    planned_mode: str | None = Field(default=None, pattern=r"^(pomodoro|free)$")
    started_at: datetime
    notes: str | None = None


class SessionEnd(BaseModel):
    ended_at: datetime
    end_reason: str = Field(default="completed", pattern=r"^(completed|stopped|timeout|error)$")
    notes: str | None = None


class SessionResponse(BaseModel):
    session_id: uuid.UUID
    user_id: uuid.UUID
    task_id: uuid.UUID | None = None
    planned_mode: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    end_reason: str | None = None
    notes: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
