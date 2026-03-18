"""
Tests for MonitoringOrchestratorService

Focuses on deterministic service behavior using mocked async DB session.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.services.monitoring_orchestrator_service import (
    MonitoringOrchestratorService,
)


@pytest.fixture
def orchestrator() -> MonitoringOrchestratorService:
    return MonitoringOrchestratorService()


@pytest.fixture
def user_id() -> UUID:
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def session_id() -> UUID:
    return UUID("87654321-4321-8765-4321-876543218765")


def _mock_db_with_session(session_obj):
    result = Mock()
    result.scalar_one_or_none.return_value = session_obj
    db = AsyncMock()
    db.execute.return_value = result
    db.flush = AsyncMock()
    return db


class TestProcessMonitoringEvent:
    @pytest.mark.asyncio
    async def test_no_active_session_returns_no_active_session(
        self,
        orchestrator: MonitoringOrchestratorService,
        user_id: UUID,
        session_id: UUID,
    ):
        db = _mock_db_with_session(None)

        res = await orchestrator.process_monitoring_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            event={"type": "phone_detected", "duration_sec": 5.0},
        )

        assert res.action == "no_active_session"

    @pytest.mark.asyncio
    async def test_distraction_warning(
        self,
        orchestrator: MonitoringOrchestratorService,
        user_id: UUID,
        session_id: UUID,
    ):
        session_obj = SimpleNamespace(
            session_id=session_id,
            user_id=user_id,
            ended_at=None,
            paused_at=None,
            pause_reason=None,
        )
        db = _mock_db_with_session(session_obj)

        res = await orchestrator.process_monitoring_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            event={"type": "phone_detected", "duration_sec": 10.0, "is_cleared": False},
        )

        assert res.action == "warning"
        assert "distraction" in res.alert_message.lower()

    @pytest.mark.asyncio
    async def test_distraction_auto_pause_sets_reason(
        self,
        orchestrator: MonitoringOrchestratorService,
        user_id: UUID,
        session_id: UUID,
    ):
        session_obj = SimpleNamespace(
            session_id=session_id,
            user_id=user_id,
            ended_at=None,
            paused_at=None,
            pause_reason=None,
        )
        db = _mock_db_with_session(session_obj)

        res = await orchestrator.process_monitoring_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            event={"type": "book_detected", "duration_sec": 25.0, "is_cleared": False},
        )

        assert res.action == "paused"
        assert session_obj.pause_reason == "distraction"
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_leave_seat_pause(
        self,
        orchestrator: MonitoringOrchestratorService,
        user_id: UUID,
        session_id: UUID,
    ):
        session_obj = SimpleNamespace(
            session_id=session_id,
            user_id=user_id,
            ended_at=None,
            paused_at=None,
            pause_reason=None,
        )
        db = _mock_db_with_session(session_obj)

        res = await orchestrator.process_monitoring_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            event={"type": "user_absent", "duration_sec": 35.0},
        )

        assert res.action == "paused"
        assert session_obj.pause_reason == "leave_seat"

    @pytest.mark.asyncio
    async def test_user_returned_countdown(
        self,
        orchestrator: MonitoringOrchestratorService,
        user_id: UUID,
        session_id: UUID,
    ):
        session_obj = SimpleNamespace(
            session_id=session_id,
            user_id=user_id,
            ended_at=None,
            paused_at=datetime.now(timezone.utc),
            pause_reason="leave_seat",
        )
        db = _mock_db_with_session(session_obj)

        res = await orchestrator.process_monitoring_event(
            db=db,
            user_id=user_id,
            session_id=session_id,
            event={"type": "user_returned", "duration_sec": 0.0},
        )

        assert res.action in ["resume_countdown", "resumed"]


class TestLiveInterventionState:
    @pytest.mark.asyncio
    async def test_default_state_when_session_missing(
        self,
        orchestrator: MonitoringOrchestratorService,
        user_id: UUID,
        session_id: UUID,
    ):
        db = _mock_db_with_session(None)

        state = await orchestrator.get_live_intervention_state(
            db=db,
            user_id=user_id,
            session_id=session_id,
        )

        assert state.escalation_level == "none"
        assert state.pause_reason is None

    @pytest.mark.asyncio
    async def test_paused_state_mapping(
        self,
        orchestrator: MonitoringOrchestratorService,
        user_id: UUID,
        session_id: UUID,
    ):
        session_obj = SimpleNamespace(
            session_id=session_id,
            user_id=user_id,
            ended_at=None,
            paused_at=datetime.now(timezone.utc),
            pause_reason="distraction",
        )
        db = _mock_db_with_session(session_obj)

        state = await orchestrator.get_live_intervention_state(
            db=db,
            user_id=user_id,
            session_id=session_id,
        )

        assert state.escalation_level == "paused"
        assert state.pause_reason == "distraction"
