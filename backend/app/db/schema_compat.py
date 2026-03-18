from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def apply_runtime_schema_compatibility(engine: AsyncEngine) -> None:
    """
    Apply non-destructive schema compatibility patches for brownfield databases.

    This prevents runtime crashes when code adds nullable columns but the existing
    database has not been migrated yet.
    """

    statements = [
        # Unit A intervention fields on study_sessions
        "ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ",
        "ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS pause_reason VARCHAR",
        # Monitoring UX fields on user_settings
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS monitoring_mode VARCHAR",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS critical_sound_enabled BOOLEAN",
    ]

    async with engine.begin() as conn:
        for stmt in statements:
            await conn.execute(text(stmt))
