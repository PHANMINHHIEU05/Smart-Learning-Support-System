import logging

import httpx

logger = logging.getLogger(__name__)


class BackendClient:
    """HTTP client for posting AI event batches to the backend API."""

    def __init__(self, base_url: str, jwt_token: str):
        self._base_url = base_url.rstrip("/")
        self._jwt_token = jwt_token

    def post_batch(self, events: list[dict]) -> bool:
        """POST a list of AI event dicts to /api/v1/ai-events/batch.

        Returns True if the backend accepted the batch (2xx), False otherwise.
        The JWT token value is never logged.
        """
        if not events:
            return True

        if not self._jwt_token:
            logger.warning(
                "JWT token is empty — skipping backend sync for %d event(s).",
                len(events),
            )
            return False

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self._base_url}/api/v1/ai-events/batch",
                    json=events,
                    headers={"Authorization": f"Bearer {self._jwt_token}"},
                )

            if response.status_code == 401:
                logger.warning(
                    "JWT token invalid or expired — batch of %d event(s) not synced.",
                    len(events),
                )
                return False

            response.raise_for_status()
            logger.debug("Successfully posted %d event(s) to backend.", len(events))
            return True

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Backend returned HTTP %s for event batch: %s",
                exc.response.status_code,
                exc,
            )
            return False
        except Exception as exc:
            logger.warning("Failed to post event batch to backend: %s", exc)
            return False
