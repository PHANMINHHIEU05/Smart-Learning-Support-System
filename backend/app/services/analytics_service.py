from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import DailySummary, EnemyStats, FocusHeatmapCell
from app.services.daily_analytics_service import (
    fetch_daily_analytics,
    fetch_live_open_block_seconds,
)


async def get_daily_summary(
    db: AsyncSession, user_id: uuid.UUID, target_date: date
) -> DailySummary:
    aggregate = await fetch_daily_analytics(db, user_id, target_date)
    if target_date == datetime.now(timezone.utc).date():
        live_seconds = await fetch_live_open_block_seconds(db, user_id, target_date)
        aggregate["focus_seconds"] += live_seconds["focus_seconds"]
        aggregate["break_seconds"] += live_seconds["break_seconds"]

    return DailySummary(
        date=target_date,
        total_focus_seconds=aggregate["focus_seconds"],
        total_break_seconds=aggregate["break_seconds"],
        distraction_count=aggregate["distraction_count"],
        fatigue_count=aggregate["fatigue_count"],
        session_count=aggregate["session_count"],
    )


async def get_focus_heatmap(
    db: AsyncSession,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> list[FocusHeatmapCell]:
    query = text(
        """
        SELECT
            day,
            slot_index,
            event_count,
            focus_score_sum,
            focus_score_samples,
            focused_event_count,
            distracted_event_count
        FROM daily_focus_heatmap
        WHERE user_id = :user_id
          AND day >= :date_from
          AND day <= :date_to
        ORDER BY day ASC, slot_index ASC
        """
    )

    result = await db.execute(
        query,
        {
            "user_id": str(user_id),
            "date_from": date_from,
            "date_to": date_to,
        },
    )
    rows = result.mappings().all()
    row_by_key = {
        ((r["day"].isoweekday() if hasattr(r["day"], "isoweekday") else 0), int(r["slot_index"])): r
        for r in rows
    }

    heatmap: list[FocusHeatmapCell] = []
    for day in range(1, 8):
        for slot in range(48):
            row = row_by_key.get((day, slot))
            hour = slot // 2
            minute = 30 if slot % 2 else 0
            if row and int(row["focus_score_samples"]) > 0:
                avg_focus = round(float(row["focus_score_sum"]) / int(row["focus_score_samples"]), 2)
            else:
                avg_focus = 0.0
            heatmap.append(
                FocusHeatmapCell(
                    day_of_week=day,
                    slot_index=slot,
                    slot_label=f"{hour:02d}:{minute:02d}",
                    avg_focus_score=avg_focus,
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
    query = text(
        """
        SELECT
            COALESCE(SUM(phone_detected_count), 0)::int AS phone_detected_count,
            COALESCE(SUM(book_detected_count), 0)::int AS book_detected_count,
            COALESCE(SUM(phone_book_count), 0)::int AS phone_book_count,
            COALESCE(SUM(drowsy_slump_count), 0)::int AS drowsy_slump_count,
            COALESCE(SUM(total_events), 0)::int AS total_events,
            COALESCE(SUM(session_count), 0)::int AS session_count
        FROM daily_analytics
        WHERE user_id = :user_id
          AND day >= :date_from
          AND day <= :date_to
        """
    )

    result = await db.execute(
        query,
        {
            "user_id": str(user_id),
            "date_from": date_from,
            "date_to": date_to,
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
