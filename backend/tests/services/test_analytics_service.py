from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.analytics_service import get_daily_summary, get_enemy_stats


def _one_row_result(row: dict[str, object]) -> Mock:
    result = Mock()
    mappings = Mock()
    mappings.one.return_value = row
    result.mappings.return_value = mappings
    return result


@pytest.mark.asyncio
async def test_daily_summary_supports_canonical_and_legacy_event_taxonomy() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _one_row_result(
                {
                    "focus_seconds": 3600,
                    "break_seconds": 600,
                    "session_count": 3,
                }
            ),
            _one_row_result(
                {
                    "distraction_count": 12,
                    "fatigue_count": 4,
                }
            ),
        ]
    )

    summary = await get_daily_summary(db, uuid.uuid4(), date(2026, 3, 20))

    assert summary.distraction_count == 12
    assert summary.fatigue_count == 4
    event_query = str(db.execute.await_args_list[1].args[0]).lower()
    assert "'phone_detected'" in event_query
    assert "'distraction_phone'" in event_query
    assert "'focus_offscreen'" in event_query
    assert "'drowsiness'" in event_query
    assert "'fatigue_drowsy'" in event_query


@pytest.mark.asyncio
async def test_enemy_stats_supports_canonical_and_legacy_event_taxonomy() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=_one_row_result(
            {
                "phone_detected_count": 10,
                "book_detected_count": 5,
                "phone_book_count": 15,
                "drowsy_slump_count": 8,
                "total_events": 40,
                "session_count": 5,
            }
        )
    )

    stats = await get_enemy_stats(
        db,
        uuid.uuid4(),
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 20),
    )

    assert stats.phone_detected_count == 10
    assert stats.book_detected_count == 5
    assert stats.phone_book_count == 15
    assert stats.drowsy_slump_count == 8
    assert stats.phone_per_session == 2.0

    query = str(db.execute.await_args.args[0]).lower()
    assert "'phone_detected'" in query
    assert "'distraction_phone'" in query
    assert "'book_detected'" in query
    assert "'distraction_book'" in query
    assert "'drowsiness'" in query
    assert "'fatigue_slump'" in query
