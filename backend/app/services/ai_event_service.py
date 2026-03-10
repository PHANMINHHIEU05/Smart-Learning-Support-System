from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_event import AiEvent
from app.schemas.ai_event import AiEventBatchCreate, AiEventCreate


async def create_event(
    db: AsyncSession, user_id: uuid.UUID, data: AiEventCreate
) -> AiEvent:
    event = AiEvent(
        event_id=uuid.uuid4(),
        user_id=user_id,
        session_id=data.session_id,
        event_type=data.event_type,
        start_at=data.start_at,
        end_at=data.end_at,
        confidence=data.confidence,
        severity=data.severity,
        payload_json=data.payload_json,
    )
    db.add(event)
    await db.flush()

    # Trigger alert evaluation (import ở đây để tránh circular import)
    from app.services.alert_service import evaluate_rules_for_event
    await evaluate_rules_for_event(db, user_id, event)

    return event


async def create_events_batch(
    db: AsyncSession, user_id: uuid.UUID, data: AiEventBatchCreate
) -> list[AiEvent]:
    events = []
    for item in data.events:
        event = AiEvent(
            event_id=uuid.uuid4(),
            user_id=user_id,
            session_id=item.session_id,
            event_type=item.event_type,
            start_at=item.start_at,
            end_at=item.end_at,
            confidence=item.confidence,
            severity=item.severity,
            payload_json=item.payload_json,
        )
        db.add(event)
        events.append(event)

    await db.flush()

    # Evaluate rules for each event
    from app.services.alert_service import evaluate_rules_for_event
    for event in events:
        await evaluate_rules_for_event(db, user_id, event)

    return events


async def list_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[AiEvent]:
    stmt = select(AiEvent).where(AiEvent.user_id == user_id)

    if event_type:
        stmt = stmt.where(AiEvent.event_type == event_type)
    if date_from:
        stmt = stmt.where(AiEvent.start_at >= date_from)
    if date_to:
        stmt = stmt.where(AiEvent.start_at <= date_to)

    stmt = stmt.order_by(AiEvent.start_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
