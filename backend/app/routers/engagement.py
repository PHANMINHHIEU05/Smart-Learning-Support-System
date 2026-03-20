from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.engagement import EngagementSummary, PenaltyHistoryResponse, WhiteNoisePreset
from app.services import engagement_service

router = APIRouter(prefix="/api/v1/engagement", tags=["Engagement"])


@router.get("/summary", response_model=EngagementSummary)
async def engagement_summary(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await engagement_service.get_engagement_summary(db, user_id)


@router.get("/penalty-history", response_model=PenaltyHistoryResponse)
async def penalty_history(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    date_from: date = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: date = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get penalty event history for user within date range"""
    return await engagement_service.get_penalty_history(db, user_id, date_from, date_to)


@router.get("/white-noise/presets", response_model=list[WhiteNoisePreset])
async def white_noise_presets(
    _user_id: uuid.UUID = Depends(get_current_user),
):
    return engagement_service.list_white_noise_presets()