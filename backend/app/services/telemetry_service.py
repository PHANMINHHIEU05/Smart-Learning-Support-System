"""
Camera telemetry service for storing and retrieving FPS metrics.
"""

import uuid
from datetime import datetime
from typing import Dict

from app.schemas.monitoring import CameraTelemetry

# In-memory cache: user_id str → latest CameraTelemetry
TELEMETRY_CACHE: Dict[str, CameraTelemetry] = {}


async def store_telemetry(telemetry: CameraTelemetry) -> None:
    """Store latest telemetry for user (in-memory cache)."""
    TELEMETRY_CACHE[str(telemetry.user_id)] = telemetry


async def get_latest_telemetry(user_id: uuid.UUID) -> CameraTelemetry | None:
    """Get most recent telemetry for user."""
    return TELEMETRY_CACHE.get(str(user_id))


async def clear_old_telemetry() -> None:
    """Optional: Cleanup task to clear stale entries after 30 min (future enhancement)."""
    pass
