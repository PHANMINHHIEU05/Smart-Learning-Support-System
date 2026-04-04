from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_taxonomy import (
    DAILY_DISTRACTION_EVENT_TYPES,
    DAILY_FATIGUE_EVENT_TYPES,
    ENEMY_BOOK_EVENT_TYPES,
    ENEMY_DROWSY_SLUMP_EVENT_TYPES,
    ENEMY_PHONE_EVENT_TYPES,
    normalize_event_type,
    sql_string_list,
)

_DISTRACTION_EVENT_SET = set(DAILY_DISTRACTION_EVENT_TYPES)
_FATIGUE_EVENT_SET = set(DAILY_FATIGUE_EVENT_TYPES)
_PHONE_EVENT_SET = set(ENEMY_PHONE_EVENT_TYPES)
_BOOK_EVENT_SET = set(ENEMY_BOOK_EVENT_TYPES)
_PHONE_BOOK_EVENT_SET = _PHONE_EVENT_SET | _BOOK_EVENT_SET
_DROWSY_SLUMP_EVENT_SET = set(ENEMY_DROWSY_SLUMP_EVENT_TYPES)

_DISTRACTION_EVENTS_SQL = sql_string_list(DAILY_DISTRACTION_EVENT_TYPES)
_FATIGUE_EVENTS_SQL = sql_string_list(DAILY_FATIGUE_EVENT_TYPES)
_PHONE_EVENTS_SQL = sql_string_list(ENEMY_PHONE_EVENT_TYPES)
_BOOK_EVENTS_SQL = sql_string_list(ENEMY_BOOK_EVENT_TYPES)
_PHONE_BOOK_EVENTS_SQL = sql_string_list((*ENEMY_PHONE_EVENT_TYPES, *ENEMY_BOOK_EVENT_TYPES))
_DROWSY_SLUMP_EVENTS_SQL = sql_string_list(ENEMY_DROWSY_SLUMP_EVENT_TYPES)

_FOCUS_HEATMAP_EVENT_TYPES_SQL = sql_string_list(
    (
        "phone_detected",
        "book_detected",
        "focus_offscreen",
        "user_absent",
        "drowsiness",
        "bad_posture",
        "face_too_close",
        "face_too_far",
    )
)

_UPSERT_SQL = text(
    """
    INSERT INTO daily_analytics (
        user_id,
        day,
        session_count,
        completed_focus_blocks,
        focus_seconds,
        break_seconds,
        distraction_count,
        fatigue_count,
        phone_detected_count,
        book_detected_count,
        phone_book_count,
        drowsy_slump_count,
        total_events,
        updated_at
    ) VALUES (
        :user_id,
        :day,
        :session_count,
        :completed_focus_blocks,
        :focus_seconds,
        :break_seconds,
        :distraction_count,
        :fatigue_count,
        :phone_detected_count,
        :book_detected_count,
        :phone_book_count,
        :drowsy_slump_count,
        :total_events,
        NOW()
    ) ON CONFLICT (user_id, day) DO UPDATE SET
        session_count = daily_analytics.session_count + EXCLUDED.session_count,
        completed_focus_blocks = daily_analytics.completed_focus_blocks + EXCLUDED.completed_focus_blocks,
        focus_seconds = daily_analytics.focus_seconds + EXCLUDED.focus_seconds,
        break_seconds = daily_analytics.break_seconds + EXCLUDED.break_seconds,
        distraction_count = daily_analytics.distraction_count + EXCLUDED.distraction_count,
        fatigue_count = daily_analytics.fatigue_count + EXCLUDED.fatigue_count,
        phone_detected_count = daily_analytics.phone_detected_count + EXCLUDED.phone_detected_count,
        book_detected_count = daily_analytics.book_detected_count + EXCLUDED.book_detected_count,
        phone_book_count = daily_analytics.phone_book_count + EXCLUDED.phone_book_count,
        drowsy_slump_count = daily_analytics.drowsy_slump_count + EXCLUDED.drowsy_slump_count,
        total_events = daily_analytics.total_events + EXCLUDED.total_events,
        updated_at = NOW()
    """
)

_FOCUS_HEATMAP_UPSERT_SQL = text(
    """
    INSERT INTO daily_focus_heatmap (
        user_id,
        day,
        slot_index,
        event_count,
        focus_score_sum,
        focus_score_samples,
        focused_event_count,
        distracted_event_count,
        updated_at
    ) VALUES (
        :user_id,
        :day,
        :slot_index,
        :event_count,
        :focus_score_sum,
        :focus_score_samples,
        :focused_event_count,
        :distracted_event_count,
        NOW()
    ) ON CONFLICT (user_id, day, slot_index) DO UPDATE SET
        event_count = daily_focus_heatmap.event_count + EXCLUDED.event_count,
        focus_score_sum = daily_focus_heatmap.focus_score_sum + EXCLUDED.focus_score_sum,
        focus_score_samples = daily_focus_heatmap.focus_score_samples + EXCLUDED.focus_score_samples,
        focused_event_count = daily_focus_heatmap.focused_event_count + EXCLUDED.focused_event_count,
        distracted_event_count = daily_focus_heatmap.distracted_event_count + EXCLUDED.distracted_event_count,
        updated_at = NOW()
    """
)

_REPLACE_SQL = text(
    f"""
    INSERT INTO daily_analytics (
        user_id,
        day,
        session_count,
        completed_focus_blocks,
        focus_seconds,
        break_seconds,
        distraction_count,
        fatigue_count,
        phone_detected_count,
        book_detected_count,
        phone_book_count,
        drowsy_slump_count,
        total_events,
        updated_at
    )
    SELECT
        combined.user_id,
        combined.day,
        combined.session_count,
        combined.completed_focus_blocks,
        combined.focus_seconds,
        combined.break_seconds,
        combined.distraction_count,
        combined.fatigue_count,
        combined.phone_detected_count,
        combined.book_detected_count,
        combined.phone_book_count,
        combined.drowsy_slump_count,
        combined.total_events,
        NOW()
    FROM (
        WITH session_rows AS (
            SELECT
                ss.user_id,
                (ss.started_at AT TIME ZONE 'UTC')::date AS day,
                COUNT(DISTINCT ss.session_id)::int AS session_count,
                COALESCE(COUNT(*) FILTER (
                    WHERE sb.block_type = 'focus'
                      AND (sb.end_at IS NOT NULL OR ss.ended_at IS NOT NULL)
                ), 0)::int AS completed_focus_blocks,
                COALESCE(SUM(
                    EXTRACT(EPOCH FROM (
                        COALESCE(sb.end_at, ss.ended_at) - sb.start_at
                    ))
                ) FILTER (
                    WHERE sb.block_type = 'focus'
                      AND (sb.end_at IS NOT NULL OR ss.ended_at IS NOT NULL)
                ), 0)::int AS focus_seconds,
                COALESCE(SUM(
                    EXTRACT(EPOCH FROM (
                        COALESCE(sb.end_at, ss.ended_at) - sb.start_at
                    ))
                ) FILTER (
                    WHERE sb.block_type IN ('break', 'long_break')
                      AND (sb.end_at IS NOT NULL OR ss.ended_at IS NOT NULL)
                ), 0)::int AS break_seconds
            FROM study_sessions ss
            LEFT JOIN session_blocks sb ON sb.session_id = ss.session_id
            GROUP BY ss.user_id, (ss.started_at AT TIME ZONE 'UTC')::date
        ),
        event_rows AS (
            SELECT
                user_id,
                (start_at AT TIME ZONE 'UTC')::date AS day,
                COALESCE(COUNT(*) FILTER (WHERE event_type IN ({_DISTRACTION_EVENTS_SQL})), 0)::int AS distraction_count,
                COALESCE(COUNT(*) FILTER (WHERE event_type IN ({_FATIGUE_EVENTS_SQL})), 0)::int AS fatigue_count,
                COALESCE(COUNT(*) FILTER (WHERE event_type IN ({_PHONE_EVENTS_SQL})), 0)::int AS phone_detected_count,
                COALESCE(COUNT(*) FILTER (WHERE event_type IN ({_BOOK_EVENTS_SQL})), 0)::int AS book_detected_count,
                COALESCE(COUNT(*) FILTER (WHERE event_type IN ({_PHONE_BOOK_EVENTS_SQL})), 0)::int AS phone_book_count,
                COALESCE(COUNT(*) FILTER (WHERE event_type IN ({_DROWSY_SLUMP_EVENTS_SQL})), 0)::int AS drowsy_slump_count,
                COUNT(*)::int AS total_events
            FROM ai_events
            GROUP BY user_id, (start_at AT TIME ZONE 'UTC')::date
        )
        SELECT
            COALESCE(s.user_id, e.user_id) AS user_id,
            COALESCE(s.day, e.day) AS day,
            COALESCE(s.session_count, 0)::int AS session_count,
            COALESCE(s.completed_focus_blocks, 0)::int AS completed_focus_blocks,
            COALESCE(s.focus_seconds, 0)::int AS focus_seconds,
            COALESCE(s.break_seconds, 0)::int AS break_seconds,
            COALESCE(e.distraction_count, 0)::int AS distraction_count,
            COALESCE(e.fatigue_count, 0)::int AS fatigue_count,
            COALESCE(e.phone_detected_count, 0)::int AS phone_detected_count,
            COALESCE(e.book_detected_count, 0)::int AS book_detected_count,
            COALESCE(e.phone_book_count, 0)::int AS phone_book_count,
            COALESCE(e.drowsy_slump_count, 0)::int AS drowsy_slump_count,
            COALESCE(e.total_events, 0)::int AS total_events
        FROM session_rows s
        FULL OUTER JOIN event_rows e
            ON e.user_id = s.user_id AND e.day = s.day
    ) AS combined
    ON CONFLICT (user_id, day) DO UPDATE SET
        session_count = EXCLUDED.session_count,
        completed_focus_blocks = EXCLUDED.completed_focus_blocks,
        focus_seconds = EXCLUDED.focus_seconds,
        break_seconds = EXCLUDED.break_seconds,
        distraction_count = EXCLUDED.distraction_count,
        fatigue_count = EXCLUDED.fatigue_count,
        phone_detected_count = EXCLUDED.phone_detected_count,
        book_detected_count = EXCLUDED.book_detected_count,
        phone_book_count = EXCLUDED.phone_book_count,
        drowsy_slump_count = EXCLUDED.drowsy_slump_count,
        total_events = EXCLUDED.total_events,
        updated_at = NOW()
    """
)

_REPLACE_FOCUS_SQL = text(
    f"""
    INSERT INTO daily_focus_heatmap (
        user_id,
        day,
        slot_index,
        event_count,
        focus_score_sum,
        focus_score_samples,
        focused_event_count,
        distracted_event_count,
        updated_at
    )
    SELECT
        aggregated.user_id,
        aggregated.day,
        aggregated.slot_index,
        aggregated.event_count,
        aggregated.focus_score_sum,
        aggregated.focus_score_samples,
        aggregated.focused_event_count,
        aggregated.distracted_event_count,
        NOW()
    FROM (
        WITH events AS (
            SELECT
                user_id,
                (start_at AT TIME ZONE 'UTC')::date AS day,
                (EXTRACT(HOUR FROM start_at)::int * 2 + CASE WHEN EXTRACT(MINUTE FROM start_at)::int >= 30 THEN 1 ELSE 0 END)::int AS slot_index,
                event_type,
                payload_json,
                CASE
                    WHEN payload_json IS NOT NULL
                         AND payload_json ? 'focus_score'
                         AND (payload_json ->> 'focus_score') ~ '^[-+]?[0-9]*\\.?[0-9]+$'
                    THEN (payload_json ->> 'focus_score')::float
                    ELSE NULL
                END AS focus_score_num
            FROM ai_events
            WHERE
                (payload_json IS NOT NULL AND payload_json ? 'focus_score')
                OR event_type = 'focus_update'
                OR event_type IN ({_FOCUS_HEATMAP_EVENT_TYPES_SQL})
        )
        SELECT
            user_id,
            day,
            slot_index,
            COUNT(*)::int AS event_count,
            COALESCE(SUM(focus_score_num), 0)::float AS focus_score_sum,
            COALESCE(COUNT(focus_score_num), 0)::int AS focus_score_samples,
            COALESCE(COUNT(*) FILTER (WHERE focus_score_num >= 70), 0)::int AS focused_event_count,
            COALESCE(COUNT(*) FILTER (
                WHERE event_type IN ({_FOCUS_HEATMAP_EVENT_TYPES_SQL})
                   OR focus_score_num < 45
            ), 0)::int AS distracted_event_count
        FROM events
        GROUP BY user_id, day, slot_index
    ) AS aggregated
    ON CONFLICT (user_id, day, slot_index) DO UPDATE SET
        event_count = EXCLUDED.event_count,
        focus_score_sum = EXCLUDED.focus_score_sum,
        focus_score_samples = EXCLUDED.focus_score_samples,
        focused_event_count = EXCLUDED.focused_event_count,
        distracted_event_count = EXCLUDED.distracted_event_count,
        updated_at = NOW()
    """
)


def _day_from_timestamp(value: datetime) -> date:
    return value.astimezone(timezone.utc).date()


def _event_buckets(event_type: str) -> dict[str, int]:
    normalized = normalize_event_type(event_type)
    buckets = {
        "distraction_count": 1 if normalized in _DISTRACTION_EVENT_SET else 0,
        "fatigue_count": 1 if normalized in _FATIGUE_EVENT_SET else 0,
        "phone_detected_count": 1 if normalized in _PHONE_EVENT_SET else 0,
        "book_detected_count": 1 if normalized in _BOOK_EVENT_SET else 0,
        "phone_book_count": 1 if normalized in _PHONE_BOOK_EVENT_SET else 0,
        "drowsy_slump_count": 1 if normalized in _DROWSY_SLUMP_EVENT_SET else 0,
        "total_events": 1,
    }
    return buckets


def _payload_dict(payload_json: Any) -> dict[str, Any]:
    if isinstance(payload_json, dict):
        return payload_json
    if isinstance(payload_json, str):
        try:
            parsed = json.loads(payload_json)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _extract_focus_score(payload_json: Any) -> float | None:
    payload = _payload_dict(payload_json)
    raw_value = payload.get("focus_score")
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    if isinstance(raw_value, str):
        try:
            return float(raw_value)
        except ValueError:
            return None
    return None


def _focus_heatmap_buckets(event_type: str, payload_json: Any) -> dict[str, float | int] | None:
    normalized = normalize_event_type(event_type)
    payload = _payload_dict(payload_json)
    focus_score = _extract_focus_score(payload)
    qualifies = (
        focus_score is not None
        or normalized == "focus_update"
        or normalized in {
            "phone_detected",
            "book_detected",
            "focus_offscreen",
            "user_absent",
            "drowsiness",
            "bad_posture",
            "face_too_close",
            "face_too_far",
        }
    )
    if not qualifies:
        return None

    return {
        "event_count": 1,
        "focus_score_sum": focus_score or 0.0,
        "focus_score_samples": 1 if focus_score is not None else 0,
        "focused_event_count": 1 if focus_score is not None and focus_score >= 70 else 0,
        "distracted_event_count": 1
        if normalized in {
            "phone_detected",
            "book_detected",
            "focus_offscreen",
            "user_absent",
            "drowsiness",
            "bad_posture",
            "face_too_close",
            "face_too_far",
        }
        or (focus_score is not None and focus_score < 45)
        else 0,
    }


def _slot_index_from_timestamp(value: datetime) -> int:
    utc_value = value.astimezone(timezone.utc)
    return utc_value.hour * 2 + (1 if utc_value.minute >= 30 else 0)


async def record_session_started(
    db: AsyncSession,
    user_id: uuid.UUID,
    started_at: datetime,
) -> None:
    await db.execute(
        _UPSERT_SQL,
        {
            "user_id": str(user_id),
            "day": _day_from_timestamp(started_at),
            "session_count": 1,
            "completed_focus_blocks": 0,
            "focus_seconds": 0,
            "break_seconds": 0,
            "distraction_count": 0,
            "fatigue_count": 0,
            "phone_detected_count": 0,
            "book_detected_count": 0,
            "phone_book_count": 0,
            "drowsy_slump_count": 0,
            "total_events": 0,
        },
    )


async def record_block_closed(
    db: AsyncSession,
    user_id: uuid.UUID,
    block_type: str,
    started_at: datetime,
    ended_at: datetime,
) -> None:
    duration_seconds = max(0, int((ended_at - started_at).total_seconds()))
    if duration_seconds <= 0:
        return

    focus_increment = 1 if block_type == "focus" else 0
    focus_seconds = duration_seconds if block_type == "focus" else 0
    break_seconds = duration_seconds if block_type in ("break", "long_break") else 0
    if focus_increment == 0 and break_seconds == 0:
        return

    await db.execute(
        _UPSERT_SQL,
        {
            "user_id": str(user_id),
            "day": _day_from_timestamp(started_at),
            "session_count": 0,
            "completed_focus_blocks": focus_increment,
            "focus_seconds": focus_seconds,
            "break_seconds": break_seconds,
            "distraction_count": 0,
            "fatigue_count": 0,
            "phone_detected_count": 0,
            "book_detected_count": 0,
            "phone_book_count": 0,
            "drowsy_slump_count": 0,
            "total_events": 0,
        },
    )


async def record_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    event_type: str,
    started_at: datetime,
) -> None:
    buckets = _event_buckets(event_type)
    await db.execute(
        _UPSERT_SQL,
        {
            "user_id": str(user_id),
            "day": _day_from_timestamp(started_at),
            "session_count": 0,
            "completed_focus_blocks": 0,
            "focus_seconds": 0,
            "break_seconds": 0,
            "distraction_count": buckets["distraction_count"],
            "fatigue_count": buckets["fatigue_count"],
            "phone_detected_count": buckets["phone_detected_count"],
            "book_detected_count": buckets["book_detected_count"],
            "phone_book_count": buckets["phone_book_count"],
            "drowsy_slump_count": buckets["drowsy_slump_count"],
            "total_events": buckets["total_events"],
        },
    )


async def record_events_batch(
    db: AsyncSession,
    user_id: uuid.UUID,
    events: Iterable[tuple[str, datetime]],
) -> None:
    by_day: dict[date, dict[str, int]] = {}
    for event_type, started_at in events:
        day = _day_from_timestamp(started_at)
        bucket = by_day.setdefault(
            day,
            {
                "session_count": 0,
                "completed_focus_blocks": 0,
                "focus_seconds": 0,
                "break_seconds": 0,
                "distraction_count": 0,
                "fatigue_count": 0,
                "phone_detected_count": 0,
                "book_detected_count": 0,
                "phone_book_count": 0,
                "drowsy_slump_count": 0,
                "total_events": 0,
            },
        )
        increments = _event_buckets(event_type)
        for key, value in increments.items():
            bucket[key] += value

    params = [
        {
            "user_id": str(user_id),
            "day": day,
            **bucket,
        }
        for day, bucket in by_day.items()
    ]
    if params:
        await db.execute(_UPSERT_SQL, params)


async def record_focus_heatmap_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    event_type: str,
    started_at: datetime,
    payload_json: Any,
) -> None:
    buckets = _focus_heatmap_buckets(event_type, payload_json)
    if buckets is None:
        return

    await db.execute(
        _FOCUS_HEATMAP_UPSERT_SQL,
        {
            "user_id": str(user_id),
            "day": _day_from_timestamp(started_at),
            "slot_index": _slot_index_from_timestamp(started_at),
            **buckets,
        },
    )


async def record_focus_heatmap_events_batch(
    db: AsyncSession,
    user_id: uuid.UUID,
    events: Iterable[tuple[str, datetime, Any]],
) -> None:
    by_key: dict[tuple[date, int], dict[str, float | int]] = {}
    for event_type, started_at, payload_json in events:
        buckets = _focus_heatmap_buckets(event_type, payload_json)
        if buckets is None:
            continue
        key = (_day_from_timestamp(started_at), _slot_index_from_timestamp(started_at))
        aggregate = by_key.setdefault(
            key,
            {
                "event_count": 0,
                "focus_score_sum": 0.0,
                "focus_score_samples": 0,
                "focused_event_count": 0,
                "distracted_event_count": 0,
            },
        )
        for field, value in buckets.items():
            aggregate[field] += value

    params = [
        {
            "user_id": str(user_id),
            "day": day,
            "slot_index": slot_index,
            **bucket,
        }
        for (day, slot_index), bucket in by_key.items()
    ]
    if params:
        await db.execute(_FOCUS_HEATMAP_UPSERT_SQL, params)


async def backfill_daily_analytics(db: AsyncSession) -> None:
    await db.execute(_REPLACE_SQL)


async def backfill_focus_heatmap_analytics(db: AsyncSession) -> None:
    await db.execute(_REPLACE_FOCUS_SQL)


async def fetch_daily_analytics(
    db: AsyncSession,
    user_id: uuid.UUID,
    day: date,
) -> dict[str, int]:
    row = (
        await db.execute(
            text(
                """
                SELECT
                    session_count,
                    completed_focus_blocks,
                    focus_seconds,
                    break_seconds,
                    distraction_count,
                    fatigue_count,
                    phone_detected_count,
                    book_detected_count,
                    phone_book_count,
                    drowsy_slump_count,
                    total_events
                FROM daily_analytics
                WHERE user_id = :user_id AND day = :day
                """
            ),
            {"user_id": str(user_id), "day": day},
        )
    ).mappings().one_or_none()

    defaults = {
        "session_count": 0,
        "completed_focus_blocks": 0,
        "focus_seconds": 0,
        "break_seconds": 0,
        "distraction_count": 0,
        "fatigue_count": 0,
        "phone_detected_count": 0,
        "book_detected_count": 0,
        "phone_book_count": 0,
        "drowsy_slump_count": 0,
        "total_events": 0,
    }
    if row is None:
        return defaults

    return {key: int(row[key]) for key in defaults}


async def fetch_live_open_block_seconds(
    db: AsyncSession,
    user_id: uuid.UUID,
    day: date,
) -> dict[str, int]:
    start_ts = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end_ts = start_ts + timedelta(days=1)
    row = (
        await db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(
                        EXTRACT(EPOCH FROM (NOW() - sb.start_at))
                    ) FILTER (WHERE sb.block_type = 'focus'), 0)::int AS focus_seconds,
                    COALESCE(SUM(
                        EXTRACT(EPOCH FROM (NOW() - sb.start_at))
                    ) FILTER (WHERE sb.block_type IN ('break', 'long_break')), 0)::int AS break_seconds
                FROM study_sessions ss
                JOIN session_blocks sb ON sb.session_id = ss.session_id
                WHERE ss.user_id = :user_id
                  AND ss.started_at >= :start_ts
                  AND ss.started_at < :end_ts
                  AND sb.end_at IS NULL
                """
            ),
            {"user_id": str(user_id), "start_ts": start_ts, "end_ts": end_ts},
        )
    ).mappings().one()

    return {
        "focus_seconds": int(row["focus_seconds"]),
        "break_seconds": int(row["break_seconds"]),
    }