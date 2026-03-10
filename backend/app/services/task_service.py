from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


async def create_task(
    db: AsyncSession, user_id: uuid.UUID, data: TaskCreate
) -> Task:
    now = datetime.now(timezone.utc)
    task = Task(
        task_id=uuid.uuid4(),
        user_id=user_id,
        **data.model_dump(),
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    await db.flush()
    return task


async def get_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> Task:
    stmt = select(Task).where(Task.task_id == task_id, Task.user_id == user_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def list_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[Task]:
    stmt = select(Task).where(Task.user_id == user_id)

    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    if due_from:
        stmt = stmt.where(Task.due_at >= due_from)
    if due_to:
        stmt = stmt.where(Task.due_at <= due_to)

    stmt = stmt.order_by(Task.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate
) -> Task:
    task = await get_task(db, user_id, task_id)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    task.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return task


async def delete_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> None:
    stmt = delete(Task).where(Task.task_id == task_id, Task.user_id == user_id)
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
