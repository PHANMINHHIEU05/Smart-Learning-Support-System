from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserSettingResponse(BaseModel):
    user_id: uuid.UUID
    timezone: str | None = None
    daily_goal_minutes: int | None = None
    pomodoro_focus_minutes: int | None = None
    pomodoro_break_minutes: int | None = None
    pomodoro_long_break_minutes: int | None = None
    pomodoro_cycles_before_long_break: int | None = None
    ai_monitoring_enabled: bool | None = None
    retention_days: int | None = None
    monitoring_mode: str | None = None
    critical_sound_enabled: bool | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserSettingUpdate(BaseModel):
    timezone: str | None = None
    daily_goal_minutes: int | None = Field(None, ge=1, le=1440)
    pomodoro_focus_minutes: int | None = Field(None, ge=1, le=120)
    pomodoro_break_minutes: int | None = Field(None, ge=1, le=60)
    pomodoro_long_break_minutes: int | None = Field(None, ge=1, le=120)
    pomodoro_cycles_before_long_break: int | None = Field(None, ge=1, le=10)
    ai_monitoring_enabled: bool | None = None
    retention_days: int | None = Field(None, ge=1, le=365)
    monitoring_mode: str | None = Field(
        None,
        pattern=r'^(external_camera|alerts_only)$',
        description="One of: external_camera, alerts_only",
    )
    critical_sound_enabled: bool | None = None
