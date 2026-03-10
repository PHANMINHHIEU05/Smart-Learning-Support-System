from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    is_enabled: bool = True
    trigger_event_type: str = Field(..., min_length=1)
    cooldown_seconds: int = Field(default=60, ge=0)
    condition_json: Any | None = None
    action_json: Any | None = None


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_enabled: bool | None = None
    trigger_event_type: str | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0)
    condition_json: Any | None = None
    action_json: Any | None = None


class AlertRuleResponse(BaseModel):
    rule_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    is_enabled: bool
    trigger_event_type: str
    cooldown_seconds: int
    condition_json: Any | None = None
    action_json: Any | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
