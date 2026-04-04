from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_event import AiEvent
from app.schemas.ai_event import AiEventBatchCreate, AiEventCreate
from app.services.daily_analytics_service import (
    record_event,
    record_events_batch,
    record_focus_heatmap_event,
    record_focus_heatmap_events_batch,
)
from app.services.event_taxonomy import (
    normalize_event_type,
    to_intervention_event_type,
)

logger = logging.getLogger("app.ai_event_service")

def _extract_payload_dict(payload_json: Any) -> dict[str, Any]:
    if isinstance(payload_json, dict):
        return payload_json

    if isinstance(payload_json, str):
        try:
            parsed = json.loads(payload_json)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}

    return {}

def _extract_duration_sec(event: AiEvent, payload: dict[str, Any]) -> float:
    for key in ("duration_sec", "duration_seconds", "duration", "durationSeconds"):
        raw_value = payload.get(key)
        if isinstance(raw_value, (int, float)):
            return max(0.0, float(raw_value))

    if event.end_at is not None and event.start_at is not None:
        return max(0.0, (event.end_at - event.start_at).total_seconds())

    return 0.0


def _build_intervention_event_payload(event: AiEvent) -> dict[str, Any] | None:
    intervention_type = to_intervention_event_type(event.event_type)
    if intervention_type is None:
        return None

    payload = _extract_payload_dict(event.payload_json)
    raw_is_cleared = payload.get("is_cleared")
    is_cleared = raw_is_cleared if isinstance(raw_is_cleared, bool) else False
    raw_message = payload.get("message")
    message = raw_message if isinstance(raw_message, str) else ""

    return {
        "type": intervention_type,
        "duration_sec": _extract_duration_sec(event, payload),
        "is_cleared": is_cleared,
        "message": message,
    }


async def _apply_intervention_orchestration(
    db: AsyncSession,
    user_id: uuid.UUID,
    event: AiEvent,
) -> None:
    if event.session_id is None:
        return

    intervention_payload = _build_intervention_event_payload(event)
    if intervention_payload is None:
        return

    try:
        from app.services.monitoring_orchestrator_service import (
            MonitoringOrchestratorService,
        )

        orchestrator = MonitoringOrchestratorService()
        await orchestrator.process_monitoring_event(
            db=db,
            user_id=user_id,
            session_id=event.session_id,
            event=intervention_payload,
        )
    except Exception:
        logger.warning(
            "Intervention orchestration failed for event %s",
            event.event_id,
            exc_info=True,
        )


async def create_event(
    db: AsyncSession, user_id: uuid.UUID, data: AiEventCreate
) -> AiEvent:
    event = AiEvent(
        event_id=uuid.uuid4(),
        user_id=user_id,
        session_id=data.session_id,
        event_type=normalize_event_type(data.event_type),
        start_at=data.start_at,
        end_at=data.end_at,
        confidence=data.confidence,
        severity=data.severity,
        payload_json=data.payload_json,
    )
    db.add(event)
    await db.flush()
    await record_event(db, user_id, event.event_type, event.start_at)
    await record_focus_heatmap_event(db, user_id, event.event_type, event.start_at, event.payload_json)

    # Trigger alert evaluation (import ở đây để tránh circular import)
    # Isolated: evaluation failure must NOT fail the event save
    try:
        from app.services.alert_service import evaluate_rules_for_event
        await evaluate_rules_for_event(db, user_id, event)
    except Exception:
        logger.warning("Alert evaluation failed for event %s", event.event_id, exc_info=True)

    # Trigger intervention orchestration for supported event types.
    # Isolated: orchestration failure must NOT fail event persistence.
    await _apply_intervention_orchestration(db, user_id, event)

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
            event_type=normalize_event_type(item.event_type),
            start_at=item.start_at,
            end_at=item.end_at,
            confidence=item.confidence,
            severity=item.severity,
            payload_json=item.payload_json,
        )
        db.add(event)
        events.append(event)

    await db.flush()
    await record_events_batch(
        db,
        user_id,
        ((event.event_type, event.start_at) for event in events),
    )
    await record_focus_heatmap_events_batch(
        db,
        user_id,
        ((event.event_type, event.start_at, event.payload_json) for event in events),
    )

    # Evaluate rules for each event
    # Isolated: evaluation failure must NOT fail the batch event save
    from app.services.alert_service import evaluate_rules_for_event
    for event in events:
        try:
            await evaluate_rules_for_event(db, user_id, event)
        except Exception:
            logger.warning("Alert evaluation failed for event %s", event.event_id, exc_info=True)
        await _apply_intervention_orchestration(db, user_id, event)

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
