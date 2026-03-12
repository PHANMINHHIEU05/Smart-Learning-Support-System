import json
import logging
import threading

logger = logging.getLogger(__name__)


class EventSyncService:
    """Background service that batches AI events and syncs them to the backend.

    Two daemon threads run concurrently:
    - flush_thread: drains the in-memory queue and POSTs to the backend every
      BATCH_INTERVAL_SECONDS. On failure, events are persisted to SQLite.
    - retry_thread: reads unsynced rows from SQLite and retries the POST every
      RETRY_INTERVAL_SECONDS.
    """

    def __init__(self, client, db_manager, settings):
        self._client = client
        self._db = db_manager
        self._settings = settings

        self._queue: list[dict] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._flush_thread = threading.Thread(
            target=self._flush_loop, daemon=True, name="EventFlush"
        )
        self._retry_thread = threading.Thread(
            target=self._retry_loop, daemon=True, name="EventRetry"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the flush and retry background threads."""
        self._flush_thread.start()
        self._retry_thread.start()
        logger.info("EventSyncService started.")

    def stop(self) -> None:
        """Signal threads to stop and wait for them to finish."""
        self._stop_event.set()
        self._flush_thread.join(timeout=5)
        self._retry_thread.join(timeout=5)
        logger.info("EventSyncService stopped.")

    def enqueue(self, event: dict) -> None:
        """Add an event to the in-memory queue.

        If the queue exceeds MAX_BATCH_SIZE * 2, the oldest entry is dropped
        to prevent unbounded memory growth.
        """
        max_size = self._settings.MAX_BATCH_SIZE * 2
        with self._lock:
            if len(self._queue) >= max_size:
                self._queue.pop(0)  # drop oldest
            self._queue.append(event)

    # ------------------------------------------------------------------
    # Internal loop methods
    # ------------------------------------------------------------------

    def _flush_loop(self) -> None:
        while not self._stop_event.wait(self._settings.BATCH_INTERVAL_SECONDS):
            self._flush_batch()

    def _flush_batch(self) -> None:
        """Drain the queue, POST to backend; persist failures to SQLite."""
        with self._lock:
            if not self._queue:
                return
            batch = self._queue[:]
            self._queue.clear()

        success = self._client.post_batch(batch)
        if not success:
            for event in batch:
                try:
                    self._db.insert_pending_event(json.dumps(event))
                except Exception as exc:
                    logger.warning("Could not persist failed event to SQLite: %s", exc)

    def _retry_loop(self) -> None:
        while not self._stop_event.wait(self._settings.RETRY_INTERVAL_SECONDS):
            self._retry_pending()

    def _retry_pending(self) -> None:
        """Load unsynced events from SQLite and retry the POST."""
        try:
            rows = self._db.get_unsynced_events(limit=self._settings.MAX_BATCH_SIZE)
        except Exception as exc:
            logger.warning("Could not load unsynced events from SQLite: %s", exc)
            return

        if not rows:
            return

        ids = []
        events = []
        for row in rows:
            try:
                ids.append(row[0])
                events.append(json.loads(row[1]))
            except (json.JSONDecodeError, IndexError) as exc:
                logger.warning(
                    "Skipping malformed pending event id=%s: %s", row[0], exc
                )

        if not events:
            return

        if self._client.post_batch(events):
            try:
                self._db.mark_events_synced(ids)
            except Exception as exc:
                logger.warning("Could not mark events as synced in SQLite: %s", exc)
