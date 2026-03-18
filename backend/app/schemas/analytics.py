from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class DailySummary(BaseModel):
    date: date
    total_focus_seconds: int = 0
    total_break_seconds: int = 0
    distraction_count: int = 0
    fatigue_count: int = 0
    session_count: int = 0


class FocusHeatmapCell(BaseModel):
    hour: int
    focus_seconds: int = 0
    avg_focus_score: float = 0.0
    event_count: int = 0


class EnemyStats(BaseModel):
    date_from: date
    date_to: date
    phone_book_count: int = 0
    drowsy_slump_count: int = 0
    total_events: int = 0
