from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.user_setting import UserSettingResponse, UserSettingUpdate
from app.services import user_settings_service

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


@router.get("/", response_model=UserSettingResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    """Lấy settings của user hiện tại. Tự động tạo defaults nếu chưa có."""
    return await user_settings_service.get_or_create_settings(db, user_id)


@router.put("/", response_model=UserSettingResponse)
async def update_settings(
    data: UserSettingUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    """Cập nhật settings. Tạo mới nếu chưa tồn tại."""
    return await user_settings_service.update_settings(db, user_id, data)
