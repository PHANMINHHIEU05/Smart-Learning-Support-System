from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.alert import AlertResponse
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleResponse, AlertRuleUpdate
from app.services import alert_service

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


# ──── Alert Rules ────

@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
async def create_rule(
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await alert_service.create_rule(db, user_id, data)


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await alert_service.list_rules(db, user_id)


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await alert_service.get_rule(db, user_id, rule_id)


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    data: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    return await alert_service.update_rule(db, user_id, rule_id, data)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    await alert_service.delete_rule(db, user_id, rule_id)


# ──── Alert History ────

@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
    session_id: uuid.UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    return await alert_service.list_alerts(
        db, user_id, session_id=session_id, offset=offset, limit=limit,
    )
