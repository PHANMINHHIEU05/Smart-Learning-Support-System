from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.engagement import EngagementSummary, PenaltyEvent, PenaltyHistoryResponse, WhiteNoisePreset

POINTS_PER_FOCUS_BLOCK = 10
POINTS_PER_DISTRACTION_EVENT = 2  # NEW: Fixed penalty per distraction
_LEVEL_THRESHOLDS = [0, 100, 250, 450, 700, 1000]

_WHITE_NOISE_PRESETS: list[WhiteNoisePreset] = [
    WhiteNoisePreset(
        id="brown-focus",
        label="Brown Focus",
        description="Warm low-frequency noise for deep focus.",
    ),
    WhiteNoisePreset(
        id="rain-soft",
        label="Soft Rain",
        description="Gentle filtered noise with light shimmer.",
    ),
    WhiteNoisePreset(
        id="cafe-air",
        label="Cafe Air",
        description="Mid-frequency ambience style texture.",
    ),
]


def _compute_level(points: int) -> tuple[int, int, int]:
    """
    Returns (level, base_threshold, next_threshold).
    Level is deterministic and monotonic.
    """
    if points < 0:
        points = 0

    for idx in range(len(_LEVEL_THRESHOLDS) - 1):
        low = _LEVEL_THRESHOLDS[idx]
        high = _LEVEL_THRESHOLDS[idx + 1]
        if low <= points < high:
            return idx + 1, low, high

    # Beyond configured thresholds, grow by 350 points per level.
    last = _LEVEL_THRESHOLDS[-1]
    extra = max(0, points - last)
    jump = 350
    extra_levels = extra // jump
    level = len(_LEVEL_THRESHOLDS) + extra_levels
    base = last + extra_levels * jump
    next_threshold = base + jump
    return level, base, next_threshold


async def _get_distraction_events_for_date(
    db: AsyncSession,
    user_id: uuid.UUID,
    target_date: date,
) -> list[PenaltyEvent]:
    """Get all distraction events for a user on a specific date"""
    query = text(
        """
        SELECT 
            event_type,
            start_at::text AS event_time
        FROM ai_events
        WHERE user_id = :user_id
          AND start_at::date = :target_date
          AND LOWER(event_type) IN (
            'distraction_phone', 'distraction_book', 'focus_offscreen',
            'fatigue_drowsy', 'fatigue_slump', 'posture_slouch', 'leave_seat_extended'
          )
        ORDER BY start_at DESC
        """
    )
    
    result = await db.execute(query, {"user_id": str(user_id), "target_date": target_date.isoformat()})
    rows = result.mappings().all()
    
    events = [
        PenaltyEvent(
            event_type=row["event_type"],
            event_time=row["event_time"],
            points_deducted=POINTS_PER_DISTRACTION_EVENT
        )
        for row in rows
    ]
    return events


def _calculate_points_deducted(events: list[PenaltyEvent]) -> int:
    """Calculate total points deducted from events"""
    return len(events) * POINTS_PER_DISTRACTION_EVENT


async def get_engagement_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> EngagementSummary:
    query = text(
        """
        SELECT
            COALESCE(COUNT(*) FILTER (
                WHERE sb.block_type = 'focus'
                  AND (sb.end_at IS NOT NULL OR ss.ended_at IS NOT NULL)
            ), 0)::int AS completed_focus_blocks
        FROM study_sessions ss
        JOIN session_blocks sb ON sb.session_id = ss.session_id
        WHERE ss.user_id = :user_id
        """
    )

    result = await db.execute(query, {"user_id": str(user_id)})
    row = result.mappings().one()

    completed_blocks = int(row["completed_focus_blocks"])
    points_earned = completed_blocks * POINTS_PER_FOCUS_BLOCK
    
    # NEW: Calculate point deductions from distraction events (today)
    from datetime import datetime
    today = datetime.now().date()
    penalty_events = await _get_distraction_events_for_date(db, user_id, today)
    points_deducted = _calculate_points_deducted(penalty_events)
    
    # NEW: Calculate net points (minimum 0)
    points_net = max(0, points_earned - points_deducted)
    
    # Use net points for level calculation
    current_level, base_points, next_level_points = _compute_level(points_net)
    span = max(1, next_level_points - base_points)
    progress_pct = int(((points_net - base_points) / span) * 100)

    return EngagementSummary(
        completed_focus_blocks=completed_blocks,
        total_points=points_net,  # Legacy field; use points_net
        points_earned=points_earned,  # NEW
        points_deducted=points_deducted,  # NEW
        points_net=points_net,  # NEW
        current_level=current_level,
        next_level_points=next_level_points,
        progress_pct=max(0, min(100, progress_pct)),
        points_per_focus_block=POINTS_PER_FOCUS_BLOCK,
    )


async def get_penalty_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> PenaltyHistoryResponse:
    """Get penalty event history for a user within a date range"""
    query = text(
        """
        SELECT 
            event_type,
            start_at::text AS event_time
        FROM ai_events
        WHERE user_id = :user_id
          AND start_at::date >= :date_from
          AND start_at::date <= :date_to
          AND LOWER(event_type) IN (
            'distraction_phone', 'distraction_book', 'focus_offscreen',
            'fatigue_drowsy', 'fatigue_slump', 'posture_slouch', 'leave_seat_extended'
          )
        ORDER BY start_at DESC
        """
    )
    
    result = await db.execute(
        query,
        {
            "user_id": str(user_id),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )
    rows = result.mappings().all()
    
    penalty_events = [
        PenaltyEvent(
            event_type=row["event_type"],
            event_time=row["event_time"],
            points_deducted=POINTS_PER_DISTRACTION_EVENT,
        )
        for row in rows
    ]
    
    total_penalty_points = len(penalty_events) * POINTS_PER_DISTRACTION_EVENT
    
    return PenaltyHistoryResponse(
        user_id=str(user_id),
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        total_penalties=total_penalty_points,
        events=penalty_events,
    )


def list_white_noise_presets() -> list[WhiteNoisePreset]:
    # Preset-only catalog by design: external URLs are intentionally disallowed.
    return _WHITE_NOISE_PRESETS