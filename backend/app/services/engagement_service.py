from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.engagement import EngagementSummary, WhiteNoisePreset

POINTS_PER_FOCUS_BLOCK = 10
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
    total_points = completed_blocks * POINTS_PER_FOCUS_BLOCK
    current_level, base_points, next_level_points = _compute_level(total_points)
    span = max(1, next_level_points - base_points)
    progress_pct = int(((total_points - base_points) / span) * 100)

    return EngagementSummary(
        completed_focus_blocks=completed_blocks,
        total_points=total_points,
        current_level=current_level,
        next_level_points=next_level_points,
        progress_pct=max(0, min(100, progress_pct)),
        points_per_focus_block=POINTS_PER_FOCUS_BLOCK,
    )


def list_white_noise_presets() -> list[WhiteNoisePreset]:
    # Preset-only catalog by design: external URLs are intentionally disallowed.
    return _WHITE_NOISE_PRESETS