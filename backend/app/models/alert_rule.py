from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_event_type: Mapped[str] = mapped_column(String, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60)
    condition_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    action_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
