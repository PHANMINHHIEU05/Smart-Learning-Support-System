from __future__ import annotations

from collections.abc import Iterable

# Canonical storage taxonomy for ai_events.event_type.
_STORAGE_EVENT_TYPE_MAP: dict[str, str] = {
    # Focus / distraction
    "focus_update": "focus_update",
    "phone_detected": "phone_detected",
    "book_detected": "book_detected",
    "focus_offscreen": "focus_offscreen",
    "distraction_phone": "phone_detected",
    "distraction_book": "book_detected",
    "distraction": "focus_offscreen",
    # Fatigue / posture
    "drowsiness": "drowsiness",
    "drowsy": "drowsiness",
    "fatigue_drowsy": "drowsiness",
    "eye_closed_long": "drowsiness",
    "bad_posture": "bad_posture",
    "posture_slouch": "bad_posture",
    "fatigue_slump": "bad_posture",
    "head_slump": "bad_posture",
    "posture_deviation": "bad_posture",
    # Presence
    "user_absent": "user_absent",
    "absent_away": "user_absent",
    "leave_seat_extended": "user_absent",
    "user_returned": "user_returned",
}

# Compatibility candidates for legacy alert-rule trigger values.
_ALERT_RULE_COMPAT_ALIASES: dict[str, tuple[str, ...]] = {
    "phone_detected": ("distraction_phone",),
    "book_detected": ("distraction_book",),
    "focus_offscreen": ("distraction",),
    "drowsiness": ("drowsy", "fatigue_drowsy", "eye_closed_long"),
    "bad_posture": ("head_slump", "posture_slouch", "fatigue_slump", "posture_deviation"),
    "user_absent": ("absent_away", "leave_seat_extended"),
}

# Mapping from canonical storage event types to intervention orchestrator event types.
_INTERVENTION_EVENT_TYPE_MAP: dict[str, str] = {
    "phone_detected": "phone_detected",
    "book_detected": "book_detected",
    "focus_offscreen": "phone_detected",
    "drowsiness": "drowsy",
    "bad_posture": "head_slump",
    "user_absent": "user_absent",
    "user_returned": "user_returned",
}

# Query sets include canonical + legacy aliases to preserve historical data counts.
DAILY_DISTRACTION_EVENT_TYPES: tuple[str, ...] = (
    "phone_detected",
    "book_detected",
    "focus_offscreen",
    "user_absent",
    "distraction_phone",
    "distraction_book",
    "distraction",
    "absent_away",
    "leave_seat_extended",
)

DAILY_FATIGUE_EVENT_TYPES: tuple[str, ...] = (
    "drowsiness",
    "bad_posture",
    "drowsy",
    "fatigue_drowsy",
    "eye_closed_long",
    "posture_slouch",
    "fatigue_slump",
    "head_slump",
    "posture_deviation",
)

ENEMY_PHONE_EVENT_TYPES: tuple[str, ...] = ("phone_detected", "distraction_phone")
ENEMY_BOOK_EVENT_TYPES: tuple[str, ...] = ("book_detected", "distraction_book")
ENEMY_DROWSY_SLUMP_EVENT_TYPES: tuple[str, ...] = DAILY_FATIGUE_EVENT_TYPES

PENALTY_EVENT_TYPES: tuple[str, ...] = (
    *DAILY_DISTRACTION_EVENT_TYPES,
    *DAILY_FATIGUE_EVENT_TYPES,
)


def normalize_event_type(event_type: str) -> str:
    normalized = event_type.strip().lower()
    if not normalized:
        return normalized
    return _STORAGE_EVENT_TYPE_MAP.get(normalized, normalized)


def normalize_rule_event_type(trigger_event_type: str) -> str:
    return normalize_event_type(trigger_event_type)


def to_intervention_event_type(event_type: str) -> str | None:
    normalized = normalize_event_type(event_type)
    return _INTERVENTION_EVENT_TYPE_MAP.get(normalized)


def alert_rule_candidates_for_event(event_type: str) -> tuple[str, ...]:
    normalized = normalize_event_type(event_type)
    aliases = _ALERT_RULE_COMPAT_ALIASES.get(normalized, ())
    ordered = [normalized, *aliases]
    seen: set[str] = set()
    deduped: list[str] = []
    for item in ordered:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return tuple(deduped)


def sql_string_list(values: Iterable[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)
