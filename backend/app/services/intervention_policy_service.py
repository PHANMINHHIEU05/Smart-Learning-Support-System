"""
Intervention Policy Service

Evaluates monitoring events against policy thresholds to determine intervention actions.
"""
from dataclasses import dataclass
from typing import Literal
import logging

logger = logging.getLogger(__name__)


@dataclass
class DistractionConfig:
    """Configuration for distraction escalation policy"""
    warn_duration_sec: float = 10.0
    pause_duration_sec: float = 20.0
    cooldown_sec: float = 60.0


@dataclass
class LeaveSeatConfig:
    """Configuration for leave-seat pause/resume policy"""
    auto_pause: bool = True
    resume_stable_sec: float = 3.0
    max_pause_min: float = 60.0


@dataclass
class EscalationDecision:
    """Result of distraction escalation evaluation"""
    action: Literal["none", "warn", "auto_pause"]
    message: str
    reason: str


@dataclass
class LeaveSeatDecision:
    """Result of leave-seat policy evaluation"""
    action: Literal["keep_running", "pause", "start_countdown", "resume"]
    countdown_sec: float | None = None


class InterventionPolicyService:
    """Centralizes intervention policy evaluation logic"""

    def __init__(
        self,
        distraction_config: DistractionConfig | None = None,
        leave_seat_config: LeaveSeatConfig | None = None,
    ):
        self.distraction_config = distraction_config or DistractionConfig()
        self.leave_seat_config = leave_seat_config or LeaveSeatConfig()

    def evaluate_distraction_escalation(
        self,
        distraction_duration_sec: float,
        is_cleared: bool = False,
    ) -> EscalationDecision:
        """
        Evaluates distraction event and determines escalation level.

        Args:
            distraction_duration_sec: elapsed seconds of continuous distraction
            is_cleared: whether distraction is now cleared

        Returns:
            EscalationDecision with action, message, reason
        """
        if is_cleared:
            return EscalationDecision(
                action="none",
                message="",
                reason="distraction_cleared",
            )

        if distraction_duration_sec >= self.distraction_config.pause_duration_sec:
            return EscalationDecision(
                action="auto_pause",
                message="Distraction detected for 20+ seconds. Pomodoro paused to refocus.",
                reason="distraction_escalated",
            )

        if distraction_duration_sec >= self.distraction_config.warn_duration_sec:
            return EscalationDecision(
                action="warn",
                message="Distraction detected for 10+ seconds. Return to work.",
                reason="distraction_warning",
            )

        return EscalationDecision(
            action="none",
            message="",
            reason="distraction_mild",
        )

    def evaluate_leave_seat_policy(
        self,
        is_user_present: bool,
        time_absent_sec: float = 0.0,
        is_currently_paused: bool = False,
    ) -> LeaveSeatDecision:
        """
        Evaluates leave-seat state and determines pause/resume action.

        Args:
            is_user_present: user currently in frame
            time_absent_sec: elapsed seconds of absence
            is_currently_paused: whether session is currently paused

        Returns:
            LeaveSeatDecision with action and optional countdown
        """
        if not self.leave_seat_config.auto_pause:
            return LeaveSeatDecision(action="keep_running")

        # User just left and session is not paused
        if not is_user_present and not is_currently_paused:
            return LeaveSeatDecision(action="pause")

        # User is back and session is paused for leave-seat; start stability check
        if is_user_present and is_currently_paused:
            return LeaveSeatDecision(
                action="start_countdown",
                countdown_sec=self.leave_seat_config.resume_stable_sec,
            )

        # Still absent or recovery complete; keep as is
        return LeaveSeatDecision(action="keep_running")
