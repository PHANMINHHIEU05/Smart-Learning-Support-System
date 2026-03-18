from __future__ import annotations

from pydantic import BaseModel


class EngagementSummary(BaseModel):
    completed_focus_blocks: int = 0
    total_points: int = 0
    current_level: int = 1
    next_level_points: int = 100
    progress_pct: int = 0
    points_per_focus_block: int = 10


class WhiteNoisePreset(BaseModel):
    id: str
    label: str
    description: str