"""
Monitoring Orchestrator Service

Routes monitoring events to timer intervention actions (pause/resume).
"""
from dataclasses import dataclass
from typing import Literal
from uuid import UUID
from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import StudySession
from .intervention_policy_service import InterventionPolicyService

logger = logging.getLogger(__name__)


@dataclass
class InterventionStateResponse:
    """Live intervention state for timer UI consumption"""

    escalation_level: Literal["none", "warning", "paused"]
    latest_alert: dict | None
    pause_reason: Literal["distraction", "leave_seat"] | None
    resume_countdown_sec: float | None
    last_update_ts: str


@dataclass
class OrchestrationResult:
    """Result of processing a monitoring event"""

    action: str
    affected_session_id: UUID | None
    alert_message: str


class MonitoringOrchestratorService:
    """Coordinates monitoring events with session intervention actions"""

    def __init__(
        self,
        policy_service: InterventionPolicyService | None = None,
    ):
        self.policy_service = policy_service or InterventionPolicyService()

    async def process_monitoring_event(
        self,
        db: AsyncSession,
        user_id: UUID,
        session_id: UUID,
        event: dict,
    ) -> OrchestrationResult:
        """
        Process monitoring event and apply intervention policy.

        Args:
            db: database session
            user_id: user ID
            session_id: study session ID
            event: monitoring event dict with type, duration, confidence, etc.

        Returns:
            OrchestrationResult describing action taken
        """
        try:
            stmt = select(StudySession).where(
                StudySession.session_id == session_id,
                StudySession.user_id == user_id,
            )
            result = await db.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if not session_obj or session_obj.ended_at is not None:
                return OrchestrationResult(
                    action="no_active_session",
                    affected_session_id=None,
                    alert_message="",
                )

            event_type = event.get("type", "")
            duration_sec = event.get("duration_sec", 0.0)
            is_cleared = event.get("is_cleared", False)

            # Route by event type
            if event_type in ["phone_detected", "book_detected"]:
                decision = self.policy_service.evaluate_distraction_escalation(
                    distraction_duration_sec=duration_sec,
                    is_cleared=is_cleared,
                )

                if decision.action == "auto_pause":
                    # Perform pause
                    session_obj.paused_at = datetime.now(timezone.utc)
                    session_obj.pause_reason = "distraction"
                    await db.flush()
                    return OrchestrationResult(
                        action="paused",
                        affected_session_id=session_id,
                        alert_message=decision.message,
                    )
                elif decision.action == "warn":
                    return OrchestrationResult(
                        action="warning",
                        affected_session_id=session_id,
                        alert_message=decision.message,
                    )

            elif event_type in ["drowsy", "eye_closed_long", "head_slump"]:
                # Log drowsiness alert but don't auto-pause
                alert_msg = event.get(
                    "message", "Drowsiness detected. Keep alert!"
                )
                return OrchestrationResult(
                    action="alert",
                    affected_session_id=session_id,
                    alert_message=alert_msg,
                )

            elif event_type == "user_absent":
                decision = self.policy_service.evaluate_leave_seat_policy(
                    is_user_present=False,
                    time_absent_sec=duration_sec,
                    is_currently_paused=session_obj.paused_at is not None,
                )

                if decision.action == "pause":
                    session_obj.paused_at = datetime.now(timezone.utc)
                    session_obj.pause_reason = "leave_seat"
                    await db.flush()
                    return OrchestrationResult(
                        action="paused",
                        affected_session_id=session_id,
                        alert_message="You left. Session paused.",
                    )

            elif event_type == "user_returned":
                is_paused_by_leave = (
                    session_obj.paused_at is not None
                    and session_obj.pause_reason == "leave_seat"
                )
                decision = self.policy_service.evaluate_leave_seat_policy(
                    is_user_present=True,
                    time_absent_sec=0.0,
                    is_currently_paused=is_paused_by_leave,
                )

                if decision.action == "start_countdown":
                    # Countdown state can be persisted in a follow-up cleanup.
                    return OrchestrationResult(
                        action="resume_countdown",
                        affected_session_id=session_id,
                        alert_message=f"Stabilizing—resume in {int(decision.countdown_sec or 0)}s",
                    )
                elif decision.action == "resume" and is_paused_by_leave:
                    session_obj.paused_at = None
                    session_obj.pause_reason = None
                    await db.flush()
                    return OrchestrationResult(
                        action="resumed",
                        affected_session_id=session_id,
                        alert_message="You're back. Resuming session.",
                    )

            return OrchestrationResult(
                action="none",
                affected_session_id=None,
                alert_message="",
            )

        except Exception as e:
            logger.error(f"Error processing monitoring event: {e}", exc_info=True)
            return OrchestrationResult(
                action="error",
                affected_session_id=None,
                alert_message="",
            )

    async def get_live_intervention_state(
        self,
        db: AsyncSession,
        user_id: UUID,
        session_id: UUID,
    ) -> InterventionStateResponse:
        """
        Get current intervention state for timer UI polling.

        Args:
            db: database session
            user_id: user ID
            session_id: study session ID

        Returns:
            InterventionStateResponse with current escalation level and pause reason
        """
        try:
            stmt = select(StudySession).where(
                StudySession.session_id == session_id,
                StudySession.user_id == user_id,
            )
            result = await db.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if not session_obj:
                return InterventionStateResponse(
                    escalation_level="none",
                    latest_alert=None,
                    pause_reason=None,
                    resume_countdown_sec=None,
                    last_update_ts="",
                )

            escalation = "paused" if session_obj.paused_at else "none"
            pause_reason = session_obj.pause_reason or None
            pause_reason_typed = (
                None
                if pause_reason not in ["distraction", "leave_seat"]
                else pause_reason
            )

            return InterventionStateResponse(
                escalation_level=escalation,
                latest_alert=None,
                pause_reason=pause_reason_typed,
                resume_countdown_sec=None,
                last_update_ts=(
                    session_obj.paused_at.isoformat()
                    if session_obj.paused_at
                    else ""
                ),
            )

        except Exception as e:
            logger.error(
                f"Error fetching intervention state: {e}", exc_info=True
            )
            return InterventionStateResponse(
                escalation_level="none",
                latest_alert=None,
                pause_reason=None,
                resume_countdown_sec=None,
                last_update_ts="",
            )
