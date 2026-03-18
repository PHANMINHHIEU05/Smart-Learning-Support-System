from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_event import AiEvent
from app.schemas.ai_event import AiEventBatchCreate, AiEventCreate

logger = logging.getLogger("app.ai_event_service")


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
    # Isolated: evaluation failure must NOT fail the event save
    try:
        from app.services.alert_service import evaluate_rules_for_event
        await evaluate_rules_for_event(db, user_id, event)
    except Exception:
        logger.warning("Alert evaluation failed for event %s", event.event_id, exc_info=True)

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
    # Isolated: evaluation failure must NOT fail the batch event save
    from app.services.alert_service import evaluate_rules_for_event
    for event in events:
        try:
            await evaluate_rules_for_event(db, user_id, event)
        except Exception:
            logger.warning("Alert evaluation failed for event %s", event.event_id, exc_info=True)

    return events


async def list_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    session_id: uuid.UUID | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[AiEvent]:
    stmt = select(AiEvent).where(AiEvent.user_id == user_id)

    if session_id:
        stmt = stmt.where(AiEvent.session_id == session_id)
    if event_type:
        stmt = stmt.where(AiEvent.event_type == event_type)
    if date_from:
        stmt = stmt.where(AiEvent.start_at >= date_from)
    if date_to:
        stmt = stmt.where(AiEvent.start_at <= date_to)

    stmt = stmt.order_by(AiEvent.start_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
