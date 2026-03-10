from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="todo", pattern=r"^(todo|doing|done|archived)$")
    priority: int | None = Field(default=None, ge=0, le=10)
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject_name: str | None = None
    tags_json: Any | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, pattern=r"^(todo|doing|done|archived)$")
    priority: int | None = Field(default=None, ge=0, le=10)
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)
    subject_name: str | None = None
    tags_json: Any | None = None


class TaskResponse(BaseModel):
    task_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None = None
    status: str
    priority: int | None = None
    due_at: datetime | None = None
    estimated_minutes: int | None = None
    subject_name: str | None = None
    tags_json: Any | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
