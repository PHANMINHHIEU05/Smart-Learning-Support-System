from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

_bearer_scheme = HTTPBearer()


def _decode_jwt(token: str) -> dict:
    """Giải mã & xác thực JWT bằng Supabase JWT secret (HS256)."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token không hợp lệ: {exc}",
        ) from exc


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
    payload = _decode_jwt(credentials.credentials)
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token thiếu claim 'sub'",
        )
    try:
        return uuid.UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Claim 'sub' không phải UUID hợp lệ",
        ) from exc
