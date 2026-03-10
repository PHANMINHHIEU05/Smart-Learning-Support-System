from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.analytics import DailySummary
from app.services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/daily-summary", response_model=DailySummary)
async def daily_summary(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    target_date: date = Query(..., description="Ngày cần xem, format: YYYY-MM-DD"),
):
    return await analytics_service.get_daily_summary(db, user_id, target_date)
