"""Tests for Unit 1: User Settings API.

Stories: US-01-01 (GET), US-01-02 (PUT)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user_setting import UserSetting
from app.schemas.user_setting import UserSettingUpdate
from app.services import user_settings_service


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _make_setting(user_id: uuid.UUID, **kwargs) -> UserSetting:
    defaults = {
        "user_id": user_id,
        "timezone": "UTC",
        "daily_goal_minutes": 120,
        "pomodoro_focus_minutes": 25,
        "pomodoro_break_minutes": 5,
        "pomodoro_long_break_minutes": 15,
        "pomodoro_cycles_before_long_break": 4,
        "ai_monitoring_enabled": True,
        "retention_days": 30,
        "updated_at": datetime.now(timezone.utc),
    }
    setting = UserSetting()
    for k, v in {**defaults, **kwargs}.items():
        setattr(setting, k, v)
    return setting


def _mock_db_execute(return_value=None) -> AsyncMock:
    """Returns an AsyncMock db whose execute() yields a row or None."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = return_value
    db.execute = AsyncMock(return_value=result_mock)
    return db


# ──────────────────────────────────────────────
# get_or_create_settings — US-01-01
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_or_create_settings_returns_existing():
    """US-01-01: Returns existing row without inserting."""
    uid = uuid.uuid4()
    existing = _make_setting(uid)
    db = _mock_db_execute(return_value=existing)

    result = await user_settings_service.get_or_create_settings(db, uid)

    assert result is existing
    db.add.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_settings_creates_defaults_when_missing():
    """US-01-01: Creates defaults when no row exists."""
    uid = uuid.uuid4()
    db = _mock_db_execute(return_value=None)

    result = await user_settings_service.get_or_create_settings(db, uid)

    db.add.assert_called_once()
    db.flush.assert_called_once()
    assert result.user_id == uid
    assert result.timezone == "UTC"
    assert result.pomodoro_focus_minutes == 25
    assert result.ai_monitoring_enabled is True


# ──────────────────────────────────────────────
# update_settings — US-01-02
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_settings_updates_existing_row():
    """US-01-02: Updates field on existing row."""
    uid = uuid.uuid4()
    existing = _make_setting(uid, pomodoro_focus_minutes=25)
    db = _mock_db_execute(return_value=existing)

    data = UserSettingUpdate(pomodoro_focus_minutes=45)
    result = await user_settings_service.update_settings(db, uid, data)

    assert result.pomodoro_focus_minutes == 45
    db.add.assert_not_called()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_update_settings_creates_row_when_missing():
    """US-01-02: Creates new row with provided + default values when no row exists."""
    uid = uuid.uuid4()
    db = _mock_db_execute(return_value=None)

    data = UserSettingUpdate(timezone="Asia/Ho_Chi_Minh", daily_goal_minutes=90)
    result = await user_settings_service.update_settings(db, uid, data)

    db.add.assert_called_once()
    db.flush.assert_called_once()
    assert result.timezone == "Asia/Ho_Chi_Minh"
    assert result.daily_goal_minutes == 90
    # Defaults should also be set
    assert result.pomodoro_focus_minutes == 25


@pytest.mark.asyncio
async def test_update_settings_only_updates_provided_fields():
    """US-01-02: Unset fields are not changed."""
    uid = uuid.uuid4()
    existing = _make_setting(uid, timezone="UTC", daily_goal_minutes=100)
    db = _mock_db_execute(return_value=existing)

    # Only update timezone, leave daily_goal_minutes untouched
    data = UserSettingUpdate(timezone="Europe/London")
    result = await user_settings_service.update_settings(db, uid, data)

    assert result.timezone == "Europe/London"
    assert result.daily_goal_minutes == 100  # unchanged


# ──────────────────────────────────────────────
# Schema validation
# ──────────────────────────────────────────────

def test_user_setting_update_rejects_invalid_focus_minutes():
    """Pydantic validation: pomodoro_focus_minutes must be 1-120."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        UserSettingUpdate(pomodoro_focus_minutes=0)

    with pytest.raises(ValidationError):
        UserSettingUpdate(pomodoro_focus_minutes=121)


def test_user_setting_update_accepts_valid_fields():
    """Pydantic validation: valid partial update passes."""
    data = UserSettingUpdate(daily_goal_minutes=60, ai_monitoring_enabled=False)
    assert data.daily_goal_minutes == 60
    assert data.ai_monitoring_enabled is False
    assert data.timezone is None
