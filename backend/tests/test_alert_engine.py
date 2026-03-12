"""Tests for Unit 2: Alert Engine.

Stories: US-02-01 (drowsiness), US-02-02 (phone), US-02-03 (configurable rules)
Tests _check_condition, _check_cooldown, evaluate_rules_for_event, and error isolation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.ai_event import AiEvent
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.services.alert_service import (
    _check_condition,
    evaluate_rules_for_event,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _make_event(
    event_type: str = "drowsiness",
    confidence: float = 0.9,
    duration_sec: float | None = None,
) -> AiEvent:
    now = datetime.now(timezone.utc)
    e = AiEvent()
    e.event_id = uuid.uuid4()
    e.user_id = uuid.uuid4()
    e.session_id = None
    e.event_type = event_type
    e.confidence = confidence
    e.severity = None
    e.payload_json = None
    e.start_at = now
    e.end_at = now + timedelta(seconds=duration_sec) if duration_sec is not None else None
    return e


def _make_rule(
    trigger_event_type: str = "drowsiness",
    is_enabled: bool = True,
    cooldown_seconds: int = 60,
    condition_json: dict | None = None,
    action_json: dict | None = None,
) -> AlertRule:
    r = AlertRule()
    r.rule_id = uuid.uuid4()
    r.user_id = uuid.uuid4()
    r.name = "Test Rule"
    r.trigger_event_type = trigger_event_type
    r.is_enabled = is_enabled
    r.cooldown_seconds = cooldown_seconds
    r.condition_json = condition_json
    r.action_json = action_json
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)
    return r


def _mock_db_with_rules(rules: list[AlertRule], last_fired: datetime | None = None) -> AsyncMock:
    """Returns a mock DB that returns given rules on first execute(), last_fired on second."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    rules_result = MagicMock()
    rules_result.scalars.return_value.all.return_value = rules

    cooldown_result = MagicMock()
    cooldown_result.scalar_one_or_none.return_value = last_fired

    db.execute = AsyncMock(side_effect=[rules_result, cooldown_result])
    return db


# ──────────────────────────────────────────────
# _check_condition — Unit tests
# ──────────────────────────────────────────────

def test_check_condition_no_condition_json_always_matches():
    """US-02-03: Rule without condition always matches."""
    rule = _make_rule(condition_json=None)
    event = _make_event(confidence=0.1)
    assert _check_condition(rule, event) is True


def test_check_condition_empty_dict_always_matches():
    rule = _make_rule(condition_json={})
    event = _make_event(confidence=0.5)
    assert _check_condition(rule, event) is True


def test_check_condition_min_confidence_passes():
    """US-02-01: Event confidence >= minConfidence passes."""
    rule = _make_rule(condition_json={"minConfidence": 0.7})
    event = _make_event(confidence=0.8)
    assert _check_condition(rule, event) is True


def test_check_condition_min_confidence_fails():
    """US-02-01: Event confidence < minConfidence is rejected."""
    rule = _make_rule(condition_json={"minConfidence": 0.9})
    event = _make_event(confidence=0.5)
    assert _check_condition(rule, event) is False


def test_check_condition_min_duration_passes():
    """US-02-01: Event duration >= minDurationSec passes."""
    rule = _make_rule(condition_json={"minDurationSec": 3.0})
    event = _make_event(duration_sec=5.0)
    assert _check_condition(rule, event) is True


def test_check_condition_min_duration_fails():
    """US-02-01: Event duration < minDurationSec is rejected."""
    rule = _make_rule(condition_json={"minDurationSec": 10.0})
    event = _make_event(duration_sec=2.0)
    assert _check_condition(rule, event) is False


def test_check_condition_min_duration_no_end_at_fails():
    """Missing end_at means duration can't be measured → reject."""
    rule = _make_rule(condition_json={"minDurationSec": 1.0})
    event = _make_event()
    event.end_at = None
    assert _check_condition(rule, event) is False


# ──────────────────────────────────────────────
# evaluate_rules_for_event — integration
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_fires_alert_when_all_checks_pass():
    """US-02-01: Alert inserted when rule matches, condition passes, cooldown elapsed."""
    rule = _make_rule(cooldown_seconds=60, condition_json=None)
    event = _make_event()
    uid = rule.user_id
    event.user_id = uid
    # last_fired was 2 minutes ago → cooldown (60s) has elapsed
    last_fired = datetime.now(timezone.utc) - timedelta(seconds=120)
    db = _mock_db_with_rules([rule], last_fired=last_fired)

    await evaluate_rules_for_event(db, uid, event)

    db.add.assert_called_once()
    added_alert = db.add.call_args[0][0]
    assert isinstance(added_alert, Alert)
    assert added_alert.rule_id == rule.rule_id
    assert added_alert.event_id == event.event_id


@pytest.mark.asyncio
async def test_evaluate_skips_alert_when_in_cooldown():
    """US-02-01: No alert fired when cooldown hasn't elapsed."""
    rule = _make_rule(cooldown_seconds=300)
    event = _make_event()
    uid = rule.user_id
    event.user_id = uid
    # last_fired was 10 seconds ago → still in 300s cooldown
    last_fired = datetime.now(timezone.utc) - timedelta(seconds=10)
    db = _mock_db_with_rules([rule], last_fired=last_fired)

    await evaluate_rules_for_event(db, uid, event)

    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_evaluate_skips_disabled_rule():
    """US-02-03: Disabled rule is never evaluated."""
    rule = _make_rule(is_enabled=False)
    event = _make_event()
    uid = rule.user_id
    event.user_id = uid
    # DB returns no rules because query filters is_enabled=true
    db = _mock_db_with_rules([])  # empty → DB-level filter simulated

    await evaluate_rules_for_event(db, uid, event)

    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_evaluate_skips_when_condition_fails():
    """US-02-01: Alert not fired when confidence below threshold."""
    rule = _make_rule(condition_json={"minConfidence": 0.9}, cooldown_seconds=0)
    event = _make_event(confidence=0.3)
    uid = rule.user_id
    event.user_id = uid
    db = _mock_db_with_rules([rule], last_fired=None)

    await evaluate_rules_for_event(db, uid, event)

    db.add.assert_not_called()


# ──────────────────────────────────────────────
# NFR-AE-02: Error isolation
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluator_exception_does_not_propagate_in_event_service():
    """NFR-AE-02: Exception in alert evaluation must NOT fail the event save."""
    from app.schemas.ai_event import AiEventCreate
    from app.services import ai_event_service
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    data = AiEventCreate(
        event_type="drowsiness",
        start_at=now,
        end_at=now,
        confidence=0.9,
        session_id=None,
        severity=None,
        payload_json=None,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    # The function is imported inside create_event via:
    # from app.services.alert_service import evaluate_rules_for_event
    # So we patch at the source module.
    with patch(
        "app.services.alert_service.evaluate_rules_for_event",
        new=AsyncMock(side_effect=RuntimeError("DB exploded")),
    ):
        # Should NOT raise — exception is swallowed and logged
        result = await ai_event_service.create_event(db, uuid.uuid4(), data)

    assert result is not None
    db.flush.assert_called()
