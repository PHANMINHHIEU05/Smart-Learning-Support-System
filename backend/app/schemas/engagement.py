from __future__ import annotations

from pydantic import BaseModel


class EngagementSummary(BaseModel):
    completed_focus_blocks: int = 0
    total_points: int = 0  # Kept for backward compatibility
    points_earned: int = 0  # NEW: Points gained from completed focus blocks
    points_deducted: int = 0  # NEW: Points deducted from distraction events
    points_net: int = 0  # NEW: Net score (earned - deducted, minimum 0)
    current_level: int = 1
    next_level_points: int = 100
    progress_pct: int = 0
    points_per_focus_block: int = 10


class PenaltyEvent(BaseModel):
    """Represents a single penalty event for analytics"""
    event_type: str
    event_time: str
    points_deducted: int = 2


class PenaltyHistoryResponse(BaseModel):
    """Response for penalty history endpoint"""
    user_id: str
    date_from: str
    date_to: str
    total_penalties: int
    events: list[PenaltyEvent]


class WhiteNoisePreset(BaseModel):
    id: str
    label: str
    description: str