from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.ai_event import AiEventBatchCreate, AiEventCreate
from app.services import ai_event_service


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_create_event_bridges_supported_event_type() -> None:
    db = _mock_db()
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    data = AiEventCreate(
        session_id=session_id,
        event_type="distraction_phone",
        start_at=now,
        end_at=now,
        confidence=0.92,
        payload_json={
            "duration_sec": 22,
            "is_cleared": False,
            "message": "Phone distraction ongoing",
        },
    )

    with patch(
        "app.services.alert_service.evaluate_rules_for_event",
        new=AsyncMock(),
    ), patch(
        "app.services.monitoring_orchestrator_service.MonitoringOrchestratorService.process_monitoring_event",
        new=AsyncMock(),
    ) as mock_process:
        created_event = await ai_event_service.create_event(db, user_id, data)

    assert created_event.event_type == "phone_detected"
    assert mock_process.await_count == 1
    called_kwargs = mock_process.await_args.kwargs
    assert called_kwargs["session_id"] == session_id
    assert called_kwargs["event"]["type"] == "phone_detected"
    assert called_kwargs["event"]["duration_sec"] == 22
    assert called_kwargs["event"]["is_cleared"] is False


@pytest.mark.asyncio
async def test_create_event_skips_bridge_for_unsupported_event_type() -> None:
    db = _mock_db()
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    data = AiEventCreate(
        session_id=session_id,
        event_type="focus_update",
        start_at=now,
        end_at=now,
        confidence=0.75,
        payload_json={"focus_score": 75},
    )

    with patch(
        "app.services.alert_service.evaluate_rules_for_event",
        new=AsyncMock(),
    ), patch(
        "app.services.monitoring_orchestrator_service.MonitoringOrchestratorService.process_monitoring_event",
        new=AsyncMock(),
    ) as mock_process:
        await ai_event_service.create_event(db, user_id, data)

    assert mock_process.await_count == 0


@pytest.mark.asyncio
async def test_create_events_batch_bridges_only_supported_events() -> None:
    db = _mock_db()
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    batch = AiEventBatchCreate(
        events=[
            AiEventCreate(
                session_id=session_id,
                event_type="drowsiness",
                start_at=now,
                end_at=now,
                confidence=0.88,
                payload_json={"duration_sec": 4},
            ),
            AiEventCreate(
                session_id=session_id,
                event_type="focus_update",
                start_at=now,
                end_at=now,
                confidence=0.64,
                payload_json={"focus_score": 64},
            ),
        ]
    )

    with patch(
        "app.services.alert_service.evaluate_rules_for_event",
        new=AsyncMock(),
    ) as mock_eval, patch(
        "app.services.monitoring_orchestrator_service.MonitoringOrchestratorService.process_monitoring_event",
        new=AsyncMock(),
    ) as mock_process:
        await ai_event_service.create_events_batch(db, user_id, batch)

    assert mock_eval.await_count == 2
    assert mock_process.await_count == 1
    called_kwargs = mock_process.await_args.kwargs
    assert called_kwargs["event"]["type"] == "drowsy"


@pytest.mark.asyncio
async def test_create_event_normalizes_distraction_alias_to_focus_offscreen() -> None:
    db = _mock_db()
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    data = AiEventCreate(
        session_id=session_id,
        event_type="distraction",
        start_at=now,
        end_at=now,
        confidence=0.81,
        payload_json={"duration_sec": 14},
    )

    with patch(
        "app.services.alert_service.evaluate_rules_for_event",
        new=AsyncMock(),
    ), patch(
        "app.services.monitoring_orchestrator_service.MonitoringOrchestratorService.process_monitoring_event",
        new=AsyncMock(),
    ) as mock_process:
        created_event = await ai_event_service.create_event(db, user_id, data)

    assert created_event.event_type == "focus_offscreen"
    assert mock_process.await_count == 1
    called_kwargs = mock_process.await_args.kwargs
    assert called_kwargs["event"]["type"] == "phone_detected"
