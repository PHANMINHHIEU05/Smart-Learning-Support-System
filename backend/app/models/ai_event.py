from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AiEvent(Base):
    __tablename__ = "ai_events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
