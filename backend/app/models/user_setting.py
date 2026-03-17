from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserSetting(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    timezone: Mapped[str | None] = mapped_column(String, nullable=True)
    daily_goal_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_focus_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_break_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_long_break_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_cycles_before_long_break: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_monitoring_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monitoring_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    critical_sound_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
