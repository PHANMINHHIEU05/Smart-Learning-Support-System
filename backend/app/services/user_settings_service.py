from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_setting import UserSetting
from app.schemas.user_setting import UserSettingUpdate

_DEFAULTS = {
    "timezone": "UTC",
    "daily_goal_minutes": 120,
    "pomodoro_focus_minutes": 25,
    "pomodoro_break_minutes": 5,
    "pomodoro_long_break_minutes": 15,
    "pomodoro_cycles_before_long_break": 4,
    "ai_monitoring_enabled": True,
    "retention_days": 30,
    "monitoring_mode": "external_camera",
    "critical_sound_enabled": True,
}


def _normalize_monitoring_mode(mode: str | None) -> str | None:
    if mode == "in_web_widget":
        return "external_camera"
    return mode


async def get_or_create_settings(db: AsyncSession, user_id: uuid.UUID) -> UserSetting:
    stmt = select(UserSetting).where(UserSetting.user_id == user_id)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()

    if setting is None:
        setting = UserSetting(
            user_id=user_id,
            updated_at=datetime.now(timezone.utc),
            **_DEFAULTS,
        )
        db.add(setting)
        await db.flush()
    else:
        normalized_mode = _normalize_monitoring_mode(setting.monitoring_mode)
        if normalized_mode != setting.monitoring_mode:
            setting.monitoring_mode = normalized_mode
            setting.updated_at = datetime.now(timezone.utc)
            await db.flush()

    return setting


async def update_settings(
    db: AsyncSession, user_id: uuid.UUID, data: UserSettingUpdate
) -> UserSetting:
    stmt = select(UserSetting).where(UserSetting.user_id == user_id)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()

    update_data = data.model_dump(exclude_unset=True)
    if "monitoring_mode" in update_data:
        update_data["monitoring_mode"] = _normalize_monitoring_mode(
            update_data.get("monitoring_mode")
        )

    if setting is None:
        # Create with defaults, overriding with provided values
        init_data = {**_DEFAULTS, **update_data}
        setting = UserSetting(
            user_id=user_id,
            updated_at=datetime.now(timezone.utc),
            **init_data,
        )
        db.add(setting)
    else:
        for key, value in update_data.items():
            setattr(setting, key, value)
        setting.updated_at = datetime.now(timezone.utc)

    await db.flush()
    return setting
