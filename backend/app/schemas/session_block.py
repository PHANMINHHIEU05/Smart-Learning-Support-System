from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BlockCreate(BaseModel):
    session_id: uuid.UUID
    block_type: str = Field(..., pattern=r"^(focus|break|long_break)$")
    start_at: datetime
    end_at: datetime | None = None


class BlockResponse(BaseModel):
    block_id: uuid.UUID
    session_id: uuid.UUID
    block_type: str
    start_at: datetime
    end_at: datetime | None = None

    model_config = {"from_attributes": True}
