from __future__ import annotations

from app.services.event_taxonomy import (
    alert_rule_candidates_for_event,
    normalize_event_type,
    to_intervention_event_type,
)


def test_normalize_event_type_maps_legacy_aliases() -> None:
    assert normalize_event_type("DISTRACTION_PHONE") == "phone_detected"
    assert normalize_event_type("distraction") == "focus_offscreen"
    assert normalize_event_type("fatigue_slump") == "bad_posture"
    assert normalize_event_type("absent_away") == "user_absent"


def test_normalize_event_type_preserves_unknown_types() -> None:
    assert normalize_event_type("custom_signal") == "custom_signal"


def test_to_intervention_event_type_supports_canonical_and_legacy() -> None:
    assert to_intervention_event_type("focus_offscreen") == "phone_detected"
    assert to_intervention_event_type("distraction") == "phone_detected"
    assert to_intervention_event_type("drowsiness") == "drowsy"
    assert to_intervention_event_type("fatigue_drowsy") == "drowsy"
    assert to_intervention_event_type("focus_update") is None


def test_alert_rule_candidates_include_legacy_aliases() -> None:
    candidates = alert_rule_candidates_for_event("drowsiness")
    assert "drowsiness" in candidates
    assert "fatigue_drowsy" in candidates
    assert "drowsy" in candidates
