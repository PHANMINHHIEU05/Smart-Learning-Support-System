from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

# Ensure Settings() can be instantiated even if backend/.env has non-boolean DEBUG.
os.environ["DEBUG"] = "false"

from app.core.config import settings
from app.core.security import get_current_user, get_user_id_from_bearer_token


@pytest.fixture
def jwt_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "unit-test-secret")
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", "")


@pytest.mark.asyncio
async def test_get_current_user_accepts_valid_local_jwt(jwt_settings: None) -> None:
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    resolved_user = await get_current_user(credentials)

    assert resolved_user == user_id


@pytest.mark.asyncio
async def test_get_user_id_from_bearer_token_accepts_valid_local_jwt(
    jwt_settings: None,
) -> None:
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

    resolved_user = await get_user_id_from_bearer_token(token)

    assert resolved_user == user_id


@pytest.mark.asyncio
async def test_get_current_user_rejects_expired_jwt(jwt_settings: None) -> None:
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_user_id_from_bearer_token_rejects_expired_jwt(
    jwt_settings: None,
) -> None:
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        await get_user_id_from_bearer_token(token)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_jwt_without_user_id(
    jwt_settings: None,
) -> None:
    payload = {
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_user_id_from_bearer_token_rejects_malformed_token(
    jwt_settings: None,
) -> None:
    with pytest.raises(HTTPException) as exc:
        await get_user_id_from_bearer_token("not-a-jwt-token")

    assert exc.value.status_code == 401
