from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.ai_event import AiEventBatchCreate, AiEventCreate, AiEventResponse
from app.services import ai_event_service

router = APIRouter(prefix="/api/v1/ai-events", tags=["AI Events"])


@router.post("/", response_model=AiEventResponse, status_code=201)
async def create_event(
    data: AiEventCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await ai_event_service.create_event(db, user_id, data)


@router.post("/batch", response_model=list[AiEventResponse], status_code=201)
async def create_events_batch(
    data: AiEventBatchCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await ai_event_service.create_events_batch(db, user_id, data)


@router.get("/", response_model=list[AiEventResponse])
async def list_events(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    event_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    return await ai_event_service.list_events(
        db, user_id,
        event_type=event_type, date_from=date_from, date_to=date_to,
        offset=offset, limit=limit,
    )
