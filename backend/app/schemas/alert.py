from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AlertResponse(BaseModel):
    alert_id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID | None = None
    rule_id: uuid.UUID | None = None
    event_id: uuid.UUID | None = None
    fired_at: datetime
    channel: str | None = None
    message: str | None = None
    payload_json: Any | None = None

    model_config = {"from_attributes": True}
