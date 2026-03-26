from __future__ import annotations

import time
import uuid
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

_bearer_scheme = HTTPBearer()
_TOKEN_CACHE_TTL_SEC = 45.0
_token_user_cache: dict[str, tuple[uuid.UUID, float]] = {}


def _decode_supabase_jwt(token: str) -> dict:
    """Xác thực access token local bằng SUPABASE_JWT_SECRET để giảm latency."""
    try:
        claims = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
        ) from exc

    user_id = claims.get("sub") or claims.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token hợp lệ nhưng không chứa user id",
        )

    return {"id": user_id}


async def _fetch_supabase_user(token: str) -> dict:
    """Xác thực access token bằng Supabase Auth API."""
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.SUPABASE_URL}/auth/v1/user", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Không thể kết nối tới Supabase Auth: {exc}",
        ) from exc

    if response.status_code == status.HTTP_200_OK:
        return response.json()

    if response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
        )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Supabase Auth trả về lỗi ngoài dự kiến: {response.status_code}",
    )


async def _verify_access_token(token: str) -> dict:
    """
    Ưu tiên verify local để tránh network call cho mỗi request polling.
    Fallback sang Supabase Auth API nếu local verify fail và có đủ config.
    """
    try:
        return _decode_supabase_jwt(token)
    except HTTPException as local_exc:
        can_fallback_remote = bool(
            settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY
        )
        if (
            local_exc.status_code == status.HTTP_401_UNAUTHORIZED
            and can_fallback_remote
        ):
            return await _fetch_supabase_user(token)
        raise


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> uuid.UUID:
    """
    Dependency — trả về user_id (UUID) đã xác thực.

    Dùng trong router:
        @router.get("/me")
        async def me(user_id: uuid.UUID = Depends(get_current_user)):
            ...
    """
    return await get_user_id_from_bearer_token(credentials.credentials)


async def get_user_id_from_bearer_token(token: str) -> uuid.UUID:
    now = time.monotonic()
    cached = _token_user_cache.get(token)
    if cached and cached[1] > now:
        return cached[0]

    user = await _verify_access_token(token)
    user_id = user.get("id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token hợp lệ nhưng phản hồi Supabase thiếu user id",
        )
    try:
        parsed = uuid.UUID(user_id)
        _token_user_cache[token] = (parsed, now + _TOKEN_CACHE_TTL_SEC)
        return parsed
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User id từ Supabase không phải UUID hợp lệ",
        ) from exc
