from __future__ import annotations

import uuid
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_bearer_scheme = HTTPBearer()


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
    user = await _fetch_supabase_user(credentials.credentials)
    user_id = user.get("id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token hợp lệ nhưng phản hồi Supabase thiếu user id",
        )
    try:
        return uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User id từ Supabase không phải UUID hợp lệ",
        ) from exc
