from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services import task_service

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await task_service.create_task(db, user_id, data)


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    status: str | None = Query(None, pattern=r"^(todo|doing|done|archived)$"),
    due_from: datetime | None = Query(None),
    due_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return await task_service.list_tasks(
        db, user_id,
        status_filter=status, due_from=due_from, due_to=due_to,
        offset=offset, limit=limit,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await task_service.get_task(db, user_id, task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await task_service.update_task(db, user_id, task_id, data)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    await task_service.delete_task(db, user_id, task_id)
