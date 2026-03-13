from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import DailySummary


async def get_daily_summary(
    db: AsyncSession, user_id: uuid.UUID, target_date: date
) -> DailySummary:
    # ── Query 1: Focus & Break time ──
    time_query = text("""
        SELECT
            COALESCE(SUM(
                EXTRACT(EPOCH FROM (sb.end_at - sb.start_at))
            ) FILTER (WHERE sb.block_type = 'focus'), 0)::int AS focus_seconds,

            COALESCE(SUM(
                EXTRACT(EPOCH FROM (sb.end_at - sb.start_at))
            ) FILTER (WHERE sb.block_type IN ('break', 'long_break')), 0)::int AS break_seconds,

            COUNT(DISTINCT ss.session_id)::int AS session_count
        FROM study_sessions ss
        JOIN session_blocks sb ON sb.session_id = ss.session_id
        WHERE ss.user_id = :user_id
          AND ss.started_at::text LIKE :target_date_prefix
          AND sb.end_at IS NOT NULL
    """)

    time_result = await db.execute(
        time_query, {"user_id": str(user_id), "target_date_prefix": target_date.isoformat() + "%"}
    )
    time_row = time_result.mappings().one()

    # ── Query 2: Distraction & Fatigue counts ──
    event_query = text("""
        SELECT
            COALESCE(COUNT(*) FILTER (
                WHERE event_type IN ('DISTRACTION_PHONE', 'FOCUS_OFFSCREEN', 'ABSENT_AWAY')
            ), 0)::int AS distraction_count,

            COALESCE(COUNT(*) FILTER (
                WHERE event_type LIKE 'FATIGUE%%'
            ), 0)::int AS fatigue_count
        FROM ai_events
        WHERE user_id = :user_id
          AND start_at::text LIKE :target_date_prefix
    """)

    event_result = await db.execute(
        event_query, {"user_id": str(user_id), "target_date_prefix": target_date.isoformat() + "%"}
    )
    event_row = event_result.mappings().one()

    return DailySummary(
        date=target_date,
        total_focus_seconds=time_row["focus_seconds"],
        total_break_seconds=time_row["break_seconds"],
        distraction_count=event_row["distraction_count"],
        fatigue_count=event_row["fatigue_count"],
        session_count=time_row["session_count"],
    )
