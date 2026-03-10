from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.study_session import SessionCreate, SessionEnd, SessionResponse
from app.services import session_service

router = APIRouter(prefix="/api/v1/sessions", tags=["Study Sessions"])


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await session_service.create_session(db, user_id, data)


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return await session_service.list_sessions(
        db, user_id, date_from=date_from, date_to=date_to,
        offset=offset, limit=limit,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await session_service.get_session(db, user_id, session_id)


@router.patch("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: uuid.UUID,
    data: SessionEnd,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await session_service.end_session(db, user_id, session_id, data)
