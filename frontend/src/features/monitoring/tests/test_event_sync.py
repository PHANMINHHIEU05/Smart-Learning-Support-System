"""Unit tests for BackendClient, EventSyncService, and MonitoringSettings."""
import json
import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# MonitoringSettings
# ---------------------------------------------------------------------------

class TestMonitoringSettings:
    def test_reads_jwt_from_env_var(self):
        with patch.dict(os.environ, {"MONITORING_JWT_TOKEN": "mytoken123"}):
            # Re-instantiate to pick up patched env
            from config.settings import MonitoringSettings
            s = MonitoringSettings()
        assert s.JWT_TOKEN == "mytoken123"

    def test_uses_defaults_when_env_vars_absent(self):
        clean_env = {k: v for k, v in os.environ.items()
                     if not k.startswith("MONITORING_")}
        with patch.dict(os.environ, clean_env, clear=True):
            from config.settings import MonitoringSettings
            s = MonitoringSettings()
        assert s.API_BASE_URL == "http://localhost:8000"
        assert s.JWT_TOKEN == ""
        assert s.BATCH_INTERVAL_SECONDS == 30
        assert s.RETRY_INTERVAL_SECONDS == 60
        assert s.MAX_BATCH_SIZE == 100

    def test_empty_token_does_not_raise(self):
        clean_env = {k: v for k, v in os.environ.items()
                     if not k.startswith("MONITORING_")}
        with patch.dict(os.environ, clean_env, clear=True):
            from config.settings import MonitoringSettings
            s = MonitoringSettings()  # Must not raise
        assert s.JWT_TOKEN == ""


# ---------------------------------------------------------------------------
# BackendClient
# ---------------------------------------------------------------------------

class TestBackendClient:
    def _make_client(self, token="validtoken"):
        from backend_client import BackendClient
        return BackendClient(base_url="http://localhost:8000", jwt_token=token)

    def test_post_batch_returns_true_on_200(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post = MagicMock(return_value=mock_response)

        with patch("backend_client.httpx.Client", return_value=mock_http):
            result = client.post_batch([{"event_type": "focus_update"}])

        assert result is True

    def test_post_batch_returns_false_on_500(self):
        import httpx as httpx_mod
        client = self._make_client()

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx_mod.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )
        mock_http.post = MagicMock(return_value=mock_response)

        with patch("backend_client.httpx.Client", return_value=mock_http):
            result = client.post_batch([{"event_type": "focus_update"}])

        assert result is False

    def test_post_batch_returns_false_on_connection_error(self):
        client = self._make_client()

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post = MagicMock(side_effect=ConnectionError("refused"))

        with patch("backend_client.httpx.Client", return_value=mock_http):
            result = client.post_batch([{"event_type": "focus_update"}])

        assert result is False

    def test_post_batch_returns_false_on_401(self):
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post = MagicMock(return_value=mock_response)

        with patch("backend_client.httpx.Client", return_value=mock_http):
            result = client.post_batch([{"event_type": "focus_update"}])

        assert result is False

    def test_post_batch_returns_true_for_empty_list(self):
        client = self._make_client()
        result = client.post_batch([])
        assert result is True

    def test_post_batch_returns_false_when_token_empty(self):
        client = self._make_client(token="")
        result = client.post_batch([{"event_type": "drowsiness"}])
        assert result is False


# ---------------------------------------------------------------------------
# EventSyncService
# ---------------------------------------------------------------------------

class TestEventSyncService:
    def _make_service(self, post_batch_returns=True):
        from event_sync_service import EventSyncService

        mock_client = MagicMock()
        mock_client.post_batch = MagicMock(return_value=post_batch_returns)

        mock_db = MagicMock()
        mock_db.insert_pending_event = MagicMock()
        mock_db.get_unsynced_events = MagicMock(return_value=[])
        mock_db.mark_events_synced = MagicMock()

        mock_settings = MagicMock()
        mock_settings.MAX_BATCH_SIZE = 100
        mock_settings.BATCH_INTERVAL_SECONDS = 30
        mock_settings.RETRY_INTERVAL_SECONDS = 60

        svc = EventSyncService(mock_client, mock_db, mock_settings)
        return svc, mock_client, mock_db

    def test_enqueue_adds_item_to_queue(self):
        svc, _, _ = self._make_service()
        svc.enqueue({"event_type": "focus_update"})
        # Access internal queue for assertion
        assert len(svc._queue) == 1
        assert svc._queue[0]["event_type"] == "focus_update"

    def test_enqueue_drops_oldest_when_overflow(self):
        svc, _, _ = self._make_service()
        # Fill queue beyond MAX_BATCH_SIZE * 2 (200)
        for i in range(200):
            svc.enqueue({"idx": i})
        # Adding one more should drop the oldest
        svc.enqueue({"idx": 200})
        assert len(svc._queue) == 200
        assert svc._queue[0]["idx"] == 1  # idx=0 was dropped

    def test_flush_batch_calls_post_batch_and_clears_queue(self):
        svc, mock_client, _ = self._make_service(post_batch_returns=True)
        svc.enqueue({"event_type": "drowsiness"})
        svc._flush_batch()
        mock_client.post_batch.assert_called_once()
        assert len(svc._queue) == 0

    def test_flush_batch_saves_to_sqlite_on_failure(self):
        svc, mock_client, mock_db = self._make_service(post_batch_returns=False)
        svc.enqueue({"event_type": "bad_posture"})
        svc._flush_batch()
        mock_db.insert_pending_event.assert_called_once()
        # The stored value should be valid JSON containing 'bad_posture'
        stored_arg = mock_db.insert_pending_event.call_args[0][0]
        assert "bad_posture" in stored_arg

    def test_retry_pending_marks_events_synced_on_success(self):
        svc, mock_client, mock_db = self._make_service(post_batch_returns=True)
        pending_row = (42, json.dumps({"event_type": "drowsiness"}))
        mock_db.get_unsynced_events.return_value = [pending_row]

        svc._retry_pending()

        mock_client.post_batch.assert_called_once()
        mock_db.mark_events_synced.assert_called_once_with([42])
