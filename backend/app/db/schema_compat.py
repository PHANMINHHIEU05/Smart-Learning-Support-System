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
        """
        CREATE TABLE IF NOT EXISTS daily_analytics (
            user_id UUID NOT NULL,
            day DATE NOT NULL,
            session_count INTEGER NOT NULL DEFAULT 0,
            completed_focus_blocks INTEGER NOT NULL DEFAULT 0,
            focus_seconds INTEGER NOT NULL DEFAULT 0,
            break_seconds INTEGER NOT NULL DEFAULT 0,
            distraction_count INTEGER NOT NULL DEFAULT 0,
            fatigue_count INTEGER NOT NULL DEFAULT 0,
            phone_detected_count INTEGER NOT NULL DEFAULT 0,
            book_detected_count INTEGER NOT NULL DEFAULT 0,
            phone_book_count INTEGER NOT NULL DEFAULT 0,
            drowsy_slump_count INTEGER NOT NULL DEFAULT 0,
            total_events INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, day)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS daily_focus_heatmap (
            user_id UUID NOT NULL,
            day DATE NOT NULL,
            slot_index INTEGER NOT NULL,
            event_count INTEGER NOT NULL DEFAULT 0,
            focus_score_sum DOUBLE PRECISION NOT NULL DEFAULT 0,
            focus_score_samples INTEGER NOT NULL DEFAULT 0,
            focused_event_count INTEGER NOT NULL DEFAULT 0,
            distracted_event_count INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, day, slot_index)
        )
        """,
        # Unit A intervention fields on study_sessions
        "ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ",
        "ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS pause_reason VARCHAR",
        # Monitoring UX fields on user_settings
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS monitoring_mode VARCHAR",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS critical_sound_enabled BOOLEAN",
        # Data normalization for case-insensitive event_type matching without LOWER(...)
        "UPDATE alert_rules SET trigger_event_type = LOWER(trigger_event_type) WHERE trigger_event_type <> LOWER(trigger_event_type)",
        # Query optimization indexes
        "CREATE INDEX IF NOT EXISTS idx_daily_analytics_day ON daily_analytics (day)",
        "CREATE INDEX IF NOT EXISTS idx_daily_focus_heatmap_day ON daily_focus_heatmap (day)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_user_rule_fired ON alerts (user_id, rule_id, fired_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_user_session_fired ON alerts (user_id, session_id, fired_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_alert_rules_user_enabled_event ON alert_rules (user_id, is_enabled, trigger_event_type)",
        "CREATE INDEX IF NOT EXISTS idx_ai_events_user_start_event_type ON ai_events (user_id, start_at DESC, event_type)",
        "CREATE INDEX IF NOT EXISTS idx_ai_events_focus_analytics ON ai_events (user_id, start_at) WHERE (payload_json IS NOT NULL AND payload_json ? 'focus_score') OR event_type IN ('phone_detected', 'book_detected', 'focus_offscreen', 'user_absent', 'drowsiness', 'bad_posture', 'face_too_close', 'face_too_far')",
    ]

    async with engine.begin() as conn:
        for stmt in statements:
            await conn.execute(text(stmt))
