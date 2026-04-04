from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session_block import SessionBlock
from app.models.study_session import StudySession
from app.schemas.study_session import SessionCreate, SessionEnd
from app.services.daily_analytics_service import record_session_started


async def create_session(
    db: AsyncSession, user_id: uuid.UUID, data: SessionCreate
) -> StudySession:
    session = StudySession(
        session_id=uuid.uuid4(),
        user_id=user_id,
        task_id=data.task_id,
        planned_mode=data.planned_mode,
        started_at=data.started_at,
        notes=data.notes,
        created_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()
    await record_session_started(db, user_id, data.started_at)
    return session


async def get_session(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> StudySession:
    stmt = select(StudySession).where(
        StudySession.session_id == session_id,
        StudySession.user_id == user_id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def end_session(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID, data: SessionEnd
) -> StudySession:
    session = await get_session(db, user_id, session_id)

    if session.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session đã kết thúc rồi",
        )

    if data.ended_at < session.started_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ended_at phải >= started_at",
        )

    stmt = (
        select(SessionBlock)
        .where(SessionBlock.session_id == session_id)
        .order_by(SessionBlock.start_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    last_block = result.scalar_one_or_none()
    if last_block is not None and last_block.end_at is None:
        if data.ended_at < last_block.start_at:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="ended_at phải >= start_at của block hiện tại",
            )
        last_block.end_at = data.ended_at
        from app.services.daily_analytics_service import record_block_closed
        await record_block_closed(db, user_id, last_block.block_type, last_block.start_at, data.ended_at)

    session.ended_at = data.ended_at
    session.end_reason = data.end_reason
    if data.notes is not None:
        session.notes = data.notes

    await db.flush()
    return session


async def pause_session(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID, reason: str
) -> StudySession:
    """Pause an active session with a reason code (distraction, leave-seat, etc)"""
    session = await get_session(db, user_id, session_id)

    if session.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot pause an ended session",
        )

    session.paused_at = datetime.now(timezone.utc)
    session.pause_reason = reason
    await db.flush()
    return session


async def resume_session(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> StudySession:
    """Resume a paused session"""
    session = await get_session(db, user_id, session_id)

    session.paused_at = None
    session.pause_reason = None
    await db.flush()
    return session


async def list_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[StudySession]:
    stmt = select(StudySession).where(StudySession.user_id == user_id)

    if date_from:
        stmt = stmt.where(StudySession.started_at >= date_from)
    if date_to:
        stmt = stmt.where(StudySession.started_at <= date_to)

    stmt = stmt.order_by(StudySession.started_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
