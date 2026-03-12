"""Shared test fixtures."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_db() -> AsyncMock:
    """AsyncSession mock with add/flush/execute stubs."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def now() -> datetime:
    return datetime.now(timezone.utc)
