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
}


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

    return setting


async def update_settings(
    db: AsyncSession, user_id: uuid.UUID, data: UserSettingUpdate
) -> UserSetting:
    stmt = select(UserSetting).where(UserSetting.user_id == user_id)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()

    update_data = data.model_dump(exclude_unset=True)

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
