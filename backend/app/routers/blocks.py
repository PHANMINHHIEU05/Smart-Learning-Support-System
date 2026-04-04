from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.session_block import BlockCreate, BlockResponse
from app.services import block_service

router = APIRouter(prefix="/api/v1/blocks", tags=["Session Blocks"])


@router.post("/", response_model=BlockResponse, status_code=201)
async def create_block(
    data: BlockCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await block_service.create_block(db, user_id, data)


@router.post("/session/{session_id}/close-latest", status_code=status.HTTP_204_NO_CONTENT)
async def close_latest_block(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    await block_service.close_latest_block(db, user_id, session_id, datetime.now(timezone.utc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/session/{session_id}", response_model=list[BlockResponse])
async def list_blocks(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await block_service.list_blocks_by_session(db, user_id, session_id)
