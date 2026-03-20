from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.engagement_service import get_engagement_summary, get_penalty_history


def _one_row_result(row: dict[str, object]) -> Mock:
    result = Mock()
    mappings = Mock()
    mappings.one.return_value = row
    result.mappings.return_value = mappings
    return result


def _rows_result(rows: list[dict[str, object]]) -> Mock:
    result = Mock()
    mappings = Mock()
    mappings.all.return_value = rows
    result.mappings.return_value = mappings
    return result


@pytest.mark.asyncio
async def test_engagement_summary_counts_penalties_with_mixed_taxonomy() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _one_row_result({"completed_focus_blocks": 12}),
            _rows_result(
                [
                    {
                        "event_id": "e-1",
                        "event_type": "phone_detected",
                        "event_time": "2026-03-20T08:00:00Z",
                    },
                    {
                        "event_id": "e-2",
                        "event_type": "distraction_phone",
                        "event_time": "2026-03-20T09:00:00Z",
                    },
                    {
                        "event_id": "e-3",
                        "event_type": "fatigue_drowsy",
                        "event_time": "2026-03-20T10:00:00Z",
                    },
                ]
            ),
        ]
    )

    summary = await get_engagement_summary(db, uuid.uuid4())

    assert summary.completed_focus_blocks == 12
    assert summary.points_earned == 120
    assert summary.points_deducted == 6
    assert summary.points_net == 114

    penalty_query = str(db.execute.await_args_list[1].args[0]).lower()
    assert "'phone_detected'" in penalty_query
    assert "'distraction_phone'" in penalty_query
    assert "'focus_offscreen'" in penalty_query
    assert "'drowsiness'" in penalty_query
    assert "'fatigue_drowsy'" in penalty_query
    assert "event_id::text as event_id" in penalty_query


@pytest.mark.asyncio
async def test_penalty_history_normalizes_legacy_event_types() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=_rows_result(
            [
                {
                    "event_id": "h-1",
                    "event_type": "distraction_phone",
                    "event_time": "2026-03-19T08:00:00Z",
                },
                {
                    "event_id": "h-2",
                    "event_type": "fatigue_slump",
                    "event_time": "2026-03-19T09:00:00Z",
                },
                {
                    "event_id": "h-3",
                    "event_type": "leave_seat_extended",
                    "event_time": "2026-03-19T10:00:00Z",
                },
            ]
        )
    )

    history = await get_penalty_history(
        db,
        uuid.uuid4(),
        date_from=date(2026, 3, 18),
        date_to=date(2026, 3, 20),
    )

    assert [event.event_type for event in history.events] == [
        "phone_detected",
        "bad_posture",
        "user_absent",
    ]
    assert history.total_penalties == 6


@pytest.mark.asyncio
async def test_penalty_history_dedupes_duplicate_event_ids() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=_rows_result(
            [
                {
                    "event_id": "dup-1",
                    "event_type": "phone_detected",
                    "event_time": "2026-03-19T08:00:00Z",
                },
                {
                    "event_id": "dup-1",
                    "event_type": "phone_detected",
                    "event_time": "2026-03-19T08:00:01Z",
                },
                {
                    "event_id": "dup-2",
                    "event_type": "drowsiness",
                    "event_time": "2026-03-19T09:00:00Z",
                },
            ]
        )
    )

    history = await get_penalty_history(
        db,
        uuid.uuid4(),
        date_from=date(2026, 3, 18),
        date_to=date(2026, 3, 20),
    )

    assert len(history.events) == 2
    assert history.total_penalties == 4
    assert [event.event_id for event in history.events] == ["dup-1", "dup-2"]


@pytest.mark.asyncio
async def test_engagement_summary_dedupes_duplicate_event_ids() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _one_row_result({"completed_focus_blocks": 2}),
            _rows_result(
                [
                    {
                        "event_id": "same-1",
                        "event_type": "phone_detected",
                        "event_time": "2026-03-20T08:00:00Z",
                    },
                    {
                        "event_id": "same-1",
                        "event_type": "phone_detected",
                        "event_time": "2026-03-20T08:00:01Z",
                    },
                ]
            ),
        ]
    )

    summary = await get_engagement_summary(db, uuid.uuid4())

    assert summary.points_earned == 20
    assert summary.points_deducted == 2
    assert summary.points_net == 18
