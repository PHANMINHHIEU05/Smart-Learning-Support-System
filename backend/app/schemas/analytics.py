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
