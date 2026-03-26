from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import DailySummary, EnemyStats, FocusHeatmapCell
from app.services.event_taxonomy import (
    DAILY_DISTRACTION_EVENT_TYPES,
    DAILY_FATIGUE_EVENT_TYPES,
    ENEMY_BOOK_EVENT_TYPES,
    ENEMY_DROWSY_SLUMP_EVENT_TYPES,
    ENEMY_PHONE_EVENT_TYPES,
    sql_string_list,
)

_DAILY_DISTRACTION_EVENTS_SQL = sql_string_list(DAILY_DISTRACTION_EVENT_TYPES)
_DAILY_FATIGUE_EVENTS_SQL = sql_string_list(DAILY_FATIGUE_EVENT_TYPES)
_ENEMY_PHONE_EVENTS_SQL = sql_string_list(ENEMY_PHONE_EVENT_TYPES)
_ENEMY_BOOK_EVENTS_SQL = sql_string_list(ENEMY_BOOK_EVENT_TYPES)
_ENEMY_PHONE_BOOK_EVENTS_SQL = sql_string_list(
    (*ENEMY_PHONE_EVENT_TYPES, *ENEMY_BOOK_EVENT_TYPES)
)
_ENEMY_DROWSY_SLUMP_EVENTS_SQL = sql_string_list(ENEMY_DROWSY_SLUMP_EVENT_TYPES)


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
    event_query = text(f"""
        SELECT
            COALESCE(COUNT(*) FILTER (
                WHERE LOWER(event_type) IN ({_DAILY_DISTRACTION_EVENTS_SQL})
            ), 0)::int AS distraction_count,

            COALESCE(COUNT(*) FILTER (
                WHERE LOWER(event_type) IN ({_DAILY_FATIGUE_EVENTS_SQL})
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
            EXTRACT(ISODOW FROM start_at)::int AS day_of_week,
            (
                EXTRACT(HOUR FROM start_at)::int * 2 +
                CASE WHEN EXTRACT(MINUTE FROM start_at)::int >= 30 THEN 1 ELSE 0 END
            )::int AS slot_index,
            COALESCE(AVG((payload_json ->> 'focus_score')::float), 0)::float AS avg_focus_score,
            COUNT(*)::int AS event_count,
            COALESCE(COUNT(*) FILTER (
                WHERE (payload_json ->> 'focus_score')::float >= 70
            ), 0)::int AS focused_event_count,
            COALESCE(COUNT(*) FILTER (
                WHERE LOWER(event_type) IN (
                    'phone_detected',
                    'book_detected',
                    'focus_offscreen',
                    'user_absent',
                    'drowsiness',
                    'bad_posture',
                    'face_too_close',
                    'face_too_far'
                )
                OR (payload_json ? 'focus_score' AND (payload_json ->> 'focus_score')::float < 45)
            ), 0)::int AS distracted_event_count
        FROM ai_events
        WHERE user_id = :user_id
          AND start_at::text >= :start_iso
          AND start_at::text < :end_iso_exclusive
          AND (
            (payload_json IS NOT NULL AND payload_json ? 'focus_score')
            OR LOWER(event_type) LIKE '%focus%'
            OR LOWER(event_type) IN (
                'phone_detected',
                'book_detected',
                'focus_offscreen',
                'user_absent',
                'drowsiness',
                'bad_posture',
                'face_too_close',
                'face_too_far'
            )
          )
        GROUP BY
            EXTRACT(ISODOW FROM start_at),
            (
                EXTRACT(HOUR FROM start_at)::int * 2 +
                CASE WHEN EXTRACT(MINUTE FROM start_at)::int >= 30 THEN 1 ELSE 0 END
            )
        ORDER BY day_of_week ASC, slot_index ASC
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
    row_by_key = {
        (int(r["day_of_week"]), int(r["slot_index"])): r
        for r in rows
    }

    heatmap: list[FocusHeatmapCell] = []
    for day in range(1, 8):
        for slot in range(48):
            row = row_by_key.get((day, slot))
            hour = slot // 2
            minute = 30 if slot % 2 else 0
            heatmap.append(
                FocusHeatmapCell(
                    day_of_week=day,
                    slot_index=slot,
                    slot_label=f"{hour:02d}:{minute:02d}",
                    avg_focus_score=round(float(row["avg_focus_score"]), 2)
                    if row
                    else 0.0,
                    event_count=int(row["event_count"]) if row else 0,
                    focused_event_count=int(row["focused_event_count"]) if row else 0,
                    distracted_event_count=int(row["distracted_event_count"]) if row else 0,
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
        f"""
        SELECT
            COALESCE(COUNT(*) FILTER (
                WHERE LOWER(event_type) IN ({_ENEMY_PHONE_EVENTS_SQL})
            ), 0)::int AS phone_detected_count,
            COALESCE(COUNT(*) FILTER (
                WHERE LOWER(event_type) IN ({_ENEMY_BOOK_EVENTS_SQL})
            ), 0)::int AS book_detected_count,
            COALESCE(COUNT(*) FILTER (
                WHERE LOWER(event_type) IN ({_ENEMY_PHONE_BOOK_EVENTS_SQL})
            ), 0)::int AS phone_book_count,
            COALESCE(COUNT(*) FILTER (
                WHERE LOWER(event_type) IN ({_ENEMY_DROWSY_SLUMP_EVENTS_SQL})
            ), 0)::int AS drowsy_slump_count,
                        COUNT(*)::int AS total_events,
                        (
                                SELECT COALESCE(COUNT(DISTINCT ss.session_id), 0)::int
                                FROM study_sessions ss
                                WHERE ss.user_id = :user_id
                                    AND ss.started_at::text >= :start_iso
                                    AND ss.started_at::text < :end_iso_exclusive
                        ) AS session_count
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

    session_count = int(row["session_count"])
    phone_detected_count = int(row["phone_detected_count"])

    return EnemyStats(
        date_from=date_from,
        date_to=date_to,
        phone_detected_count=phone_detected_count,
        book_detected_count=int(row["book_detected_count"]),
        phone_book_count=int(row["phone_book_count"]),
        drowsy_slump_count=int(row["drowsy_slump_count"]),
        session_count=session_count,
        phone_per_session=round(
            phone_detected_count / session_count,
            2,
        )
        if session_count > 0
        else 0.0,
        total_events=int(row["total_events"]),
    )
