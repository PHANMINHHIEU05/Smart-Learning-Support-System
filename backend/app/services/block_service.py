from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session_block import SessionBlock
from app.models.study_session import StudySession
from app.schemas.session_block import BlockCreate
from app.services.daily_analytics_service import record_block_closed


async def _verify_session_ownership(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> StudySession:
    """Kiểm tra session có thuộc user không."""
    stmt = select(StudySession).where(
        StudySession.session_id == session_id,
        StudySession.user_id == user_id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def create_block(
    db: AsyncSession, user_id: uuid.UUID, data: BlockCreate
) -> SessionBlock:
    # 1. Verify ownership
    await _verify_session_ownership(db, user_id, data.session_id)

    # 2. Validate chronological consistency
    stmt = (
        select(SessionBlock)
        .where(SessionBlock.session_id == data.session_id)
        .order_by(SessionBlock.start_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    last_block = result.scalar_one_or_none()

    if last_block is not None:
        if last_block.end_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Block trước chưa kết thúc (end_at is NULL). Hãy kết thúc block cũ trước.",
            )
        if data.start_at < last_block.end_at:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start_at phải >= end_at của block trước (thời gian chồng chéo)",
            )

    # 3. Create
    block = SessionBlock(
        block_id=uuid.uuid4(),
        session_id=data.session_id,
        block_type=data.block_type,
        start_at=data.start_at,
        end_at=data.end_at,
    )
    db.add(block)
    await db.flush()
    return block


async def close_latest_block(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    ended_at: datetime,
) -> SessionBlock | None:
    await _verify_session_ownership(db, user_id, session_id)

    stmt = (
        select(SessionBlock)
        .where(SessionBlock.session_id == session_id)
        .order_by(SessionBlock.start_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    last_block = result.scalar_one_or_none()
    if last_block is None:
        return None

    if ended_at < last_block.start_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ended_at phải >= start_at của block hiện tại",
        )

    previous_end_at = last_block.end_at
    if previous_end_at is None:
        delta_start = last_block.start_at
    else:
        if ended_at <= previous_end_at:
            return last_block
        delta_start = previous_end_at

    last_block.end_at = ended_at
    await record_block_closed(db, user_id, last_block.block_type, delta_start, ended_at)
    await db.flush()

    return last_block


async def heartbeat_block(
    db: AsyncSession,
    user_id: uuid.UUID,
    block_id: uuid.UUID,
    ended_at: datetime,
) -> SessionBlock:
    stmt = (
        select(SessionBlock)
        .join(StudySession, SessionBlock.session_id == StudySession.session_id)
        .where(
            SessionBlock.block_id == block_id,
            StudySession.user_id == user_id,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    block = result.scalar_one_or_none()
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")

    if ended_at < block.start_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ended_at phải >= start_at của block hiện tại",
        )

    previous_end_at = block.end_at
    if previous_end_at is None:
        delta_start = block.start_at
    else:
        if ended_at <= previous_end_at:
            return block
        delta_start = previous_end_at

    block.end_at = ended_at
    await record_block_closed(db, user_id, block.block_type, delta_start, ended_at)
    await db.flush()
    return block


async def list_blocks_by_session(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> list[SessionBlock]:
    # Verify ownership first
    await _verify_session_ownership(db, user_id, session_id)

    stmt = (
        select(SessionBlock)
        .where(SessionBlock.session_id == session_id)
        .order_by(SessionBlock.start_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
