from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_event import AiEvent
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleUpdate
from app.services.event_taxonomy import (
    alert_rule_candidates_for_event,
    normalize_rule_event_type,
)

logger = logging.getLogger("app.alert_service")


_DEFAULT_ALERT_RULES: tuple[dict[str, object], ...] = (
    {
        "name": "Drowsiness Warning",
        "trigger_event_type": "drowsiness",
        "cooldown_seconds": 20,
        "condition_json": {"minConfidence": 0.30},
        "action_json": {"toast": True, "severity": "critical"},
    },
    {
        "name": "Bad Posture Warning",
        "trigger_event_type": "bad_posture",
        "cooldown_seconds": 20,
        "condition_json": {"minConfidence": 0.25},
        "action_json": {"toast": True, "severity": "medium"},
    },
    {
        "name": "Too Close To Screen",
        "trigger_event_type": "face_too_close",
        "cooldown_seconds": 20,
        "condition_json": {"minConfidence": 0.20},
        "action_json": {"toast": True, "severity": "medium"},
    },
    {
        "name": "Too Far From Screen",
        "trigger_event_type": "face_too_far",
        "cooldown_seconds": 20,
        "condition_json": {"minConfidence": 0.20},
        "action_json": {"toast": True, "severity": "medium"},
    },
    {
        "name": "Distraction Warning",
        "trigger_event_type": "focus_offscreen",
        "cooldown_seconds": 15,
        "condition_json": {"minConfidence": 0.25},
        "action_json": {"toast": True, "severity": "medium"},
    },
    {
        "name": "Phone Detected",
        "trigger_event_type": "phone_detected",
        "cooldown_seconds": 15,
        "condition_json": {"minConfidence": 0.20},
        "action_json": {"toast": True, "severity": "critical"},
    },
)


async def ensure_default_rules(db: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = select(func.count(AlertRule.rule_id)).where(AlertRule.user_id == user_id)
    result = await db.execute(stmt)
    total = int(result.scalar_one() or 0)
    if total > 0:
        return 0

    now = datetime.now(timezone.utc)
    created = 0
    for template in _DEFAULT_ALERT_RULES:
        payload = dict(template)
        trigger_event_type = normalize_rule_event_type(str(payload.pop("trigger_event_type")))
        rule = AlertRule(
            rule_id=uuid.uuid4(),
            user_id=user_id,
            name=str(payload["name"]),
            is_enabled=True,
            trigger_event_type=trigger_event_type,
            cooldown_seconds=int(payload.get("cooldown_seconds", 20)),
            condition_json=payload.get("condition_json"),
            action_json=payload.get("action_json"),
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        created += 1

    await db.flush()
    logger.info("Seeded %s default alert rules for user %s", created, user_id)
    return created


# ────────────────────────── CRUD Alert Rules ──────────────────────────

async def create_rule(
    db: AsyncSession, user_id: uuid.UUID, data: AlertRuleCreate
) -> AlertRule:
    payload = data.model_dump()
    payload["trigger_event_type"] = normalize_rule_event_type(payload["trigger_event_type"])
    rule = AlertRule(
        rule_id=uuid.uuid4(),
        user_id=user_id,
        **payload,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(rule)
    await db.flush()
    return rule


async def get_rule(
    db: AsyncSession, user_id: uuid.UUID, rule_id: uuid.UUID
) -> AlertRule:
    stmt = select(AlertRule).where(AlertRule.rule_id == rule_id, AlertRule.user_id == user_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return rule


async def list_rules(
    db: AsyncSession, user_id: uuid.UUID
) -> list[AlertRule]:
    stmt = select(AlertRule).where(AlertRule.user_id == user_id).order_by(AlertRule.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_rule(
    db: AsyncSession, user_id: uuid.UUID, rule_id: uuid.UUID, data: AlertRuleUpdate
) -> AlertRule:
    rule = await get_rule(db, user_id, rule_id)
    update_data = data.model_dump(exclude_unset=True)
    if "trigger_event_type" in update_data:
        update_data["trigger_event_type"] = normalize_rule_event_type(
            update_data["trigger_event_type"]
        )
    for key, value in update_data.items():
        setattr(rule, key, value)
    rule.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return rule


async def delete_rule(
    db: AsyncSession, user_id: uuid.UUID, rule_id: uuid.UUID
) -> None:
    stmt = delete(AlertRule).where(AlertRule.rule_id == rule_id, AlertRule.user_id == user_id)
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")


# ────────────────────────── List Alerts ──────────────────────────

async def list_alerts(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    session_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Alert]:
    stmt = select(Alert).where(Alert.user_id == user_id)
    if session_id:
        stmt = stmt.where(Alert.session_id == session_id)
    stmt = stmt.order_by(Alert.fired_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ────────────────────────── Rule Evaluation Engine ──────────────────────────

async def evaluate_rules_for_event(
    db: AsyncSession, user_id: uuid.UUID, event: AiEvent
) -> None:
    """
    Được gọi SAU KHI insert ai_event.
    Tìm tất cả alert_rules match → check condition → check cooldown → fire alert.
    """
    # 1. Lấy rules match event_type
    event_type_candidates = alert_rule_candidates_for_event(event.event_type)
    stmt = select(AlertRule).where(
        AlertRule.user_id == user_id,
        AlertRule.is_enabled == True,  # noqa: E712
        AlertRule.trigger_event_type.in_(event_type_candidates),
    )
    result = await db.execute(stmt)
    rules = result.scalars().all()
    if not rules:
        return

    rule_ids = [rule.rule_id for rule in rules]
    cooldown_stmt = (
        select(Alert.rule_id, func.max(Alert.fired_at))
        .where(
            Alert.user_id == user_id,
            Alert.rule_id.in_(rule_ids),
        )
        .group_by(Alert.rule_id)
    )
    cooldown_result = await db.execute(cooldown_stmt)
    last_fired_by_rule = {
        rule_id: fired_at
        for rule_id, fired_at in cooldown_result.all()
    }

    now = datetime.now(timezone.utc)

    for rule in rules:
        # 2a. Check condition_json
        if not _check_condition(rule, event):
            logger.debug("Rule %s: condition không match", rule.rule_id)
            continue

        # 2b. Check cooldown
        if not _check_cooldown(rule, now, last_fired_by_rule.get(rule.rule_id)):
            logger.debug("Rule %s: đang trong cooldown", rule.rule_id)
            continue

        # 2c. Fire alert!
        action_payload = rule.action_json if isinstance(rule.action_json, dict) else {}
        alert = Alert(
            alert_id=uuid.uuid4(),
            user_id=user_id,
            session_id=event.session_id,
            rule_id=rule.rule_id,
            event_id=event.event_id,
            fired_at=now,
            channel=_get_channel(rule),
            message=f"[{rule.name}] Phát hiện: {event.event_type}",
            payload_json={
                **action_payload,
                "event_type": event.event_type,
                "severity": action_payload.get("severity", event.severity or "medium"),
                "rule_name": rule.name,
                "confidence": event.confidence,
            },
        )
        db.add(alert)
        logger.info("Alert fired: rule=%s, event=%s", rule.name, event.event_type)

    await db.flush()


def _check_condition(rule: AlertRule, event: AiEvent) -> bool:
    """Kiểm tra condition_json có match với event không."""
    cond = rule.condition_json
    if not cond or not isinstance(cond, dict):
        return True  # không có condition → luôn match

    # Check minConfidence
    min_conf = cond.get("minConfidence")
    if min_conf is not None and event.confidence < min_conf:
        return False

    # Check minDurationSec
    min_dur = cond.get("minDurationSec")
    if min_dur is not None:
        if event.end_at is None or event.start_at is None:
            return False
        duration = (event.end_at - event.start_at).total_seconds()
        if duration < min_dur:
            return False

    return True


def _check_cooldown(rule: AlertRule, now: datetime, last_fired: datetime | None) -> bool:
    """
    Kiểm tra đã qua cooldown chưa.
    Return True nếu OK (đã qua cooldown hoặc chưa có alert nào).
    """
    if rule.cooldown_seconds <= 0:
        return True

    if last_fired is None:
        return True  # chưa có alert nào → OK

    elapsed = (now - last_fired).total_seconds()
    return elapsed >= rule.cooldown_seconds


def _get_channel(rule: AlertRule) -> str:
    """Lấy channel từ action_json, mặc định 'toast'."""
    if rule.action_json and isinstance(rule.action_json, dict):
        if rule.action_json.get("toast"):
            return "toast"
        if rule.action_json.get("sound"):
            return "sound"
    return "toast"
