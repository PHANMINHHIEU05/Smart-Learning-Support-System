from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import DailySummary, EnemyStats, FocusHeatmapCell


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


async def get_focus_heatmap(
    db: AsyncSession,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> list[FocusHeatmapCell]:
    start_iso = date_from.isoformat()
    end_iso_exclusive = (date_to + timedelta(days=1)).isoformat()

    query = text(
        """
        SELECT
            EXTRACT(HOUR FROM start_at)::int AS hour,
            COALESCE(SUM(CASE
                WHEN end_at IS NOT NULL THEN EXTRACT(EPOCH FROM (end_at - start_at))
                ELSE 0
            END), 0)::int AS focus_seconds,
            COALESCE(AVG((payload_json ->> 'focus_score')::float), 0)::float AS avg_focus_score,
            COUNT(*)::int AS event_count
        FROM ai_events
        WHERE user_id = :user_id
          AND start_at::text >= :start_iso
          AND start_at::text < :end_iso_exclusive
          AND (
            (payload_json IS NOT NULL AND payload_json ? 'focus_score')
            OR LOWER(event_type) LIKE '%focus%'
          )
        GROUP BY EXTRACT(HOUR FROM start_at)
        ORDER BY hour ASC
        """
    )

    result = await db.execute(
        query,
        {
            "user_id": str(user_id),
            "start_iso": start_iso,
            "end_iso_exclusive": end_iso_exclusive,
        },
    )
    rows = result.mappings().all()
    row_by_hour = {int(r["hour"]): r for r in rows}

    heatmap: list[FocusHeatmapCell] = []
    for hour in range(24):
        row = row_by_hour.get(hour)
        heatmap.append(
            FocusHeatmapCell(
                hour=hour,
                focus_seconds=int(row["focus_seconds"]) if row else 0,
                avg_focus_score=round(float(row["avg_focus_score"]), 2)
                if row
                else 0.0,
                event_count=int(row["event_count"]) if row else 0,
            )
        )
    return heatmap


async def get_enemy_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> EnemyStats:
    start_iso = date_from.isoformat()
    end_iso_exclusive = (date_to + timedelta(days=1)).isoformat()

    query = text(
        """
        SELECT
            COALESCE(COUNT(*) FILTER (
                WHERE LOWER(event_type) LIKE '%phone%'
                   OR LOWER(event_type) LIKE '%book%'
            ), 0)::int AS phone_book_count,
            COALESCE(COUNT(*) FILTER (
                WHERE LOWER(event_type) LIKE '%drows%'
                   OR LOWER(event_type) LIKE '%slump%'
                   OR LOWER(event_type) LIKE '%fatigue%'
                   OR LOWER(event_type) LIKE '%eye_closed%'
            ), 0)::int AS drowsy_slump_count,
            COUNT(*)::int AS total_events
        FROM ai_events
        WHERE user_id = :user_id
          AND start_at::text >= :start_iso
          AND start_at::text < :end_iso_exclusive
        """
    )

    result = await db.execute(
        query,
        {
            "user_id": str(user_id),
            "start_iso": start_iso,
            "end_iso_exclusive": end_iso_exclusive,
        },
    )
    row = result.mappings().one()

    return EnemyStats(
        date_from=date_from,
        date_to=date_to,
        phone_book_count=int(row["phone_book_count"]),
        drowsy_slump_count=int(row["drowsy_slump_count"]),
        total_events=int(row["total_events"]),
    )
