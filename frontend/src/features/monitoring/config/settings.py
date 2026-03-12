import os
import logging

logger = logging.getLogger(__name__)


class MonitoringSettings:
    """Settings for the AI monitoring module, loaded from environment variables."""

    def __init__(self):
        self.API_BASE_URL: str = os.environ.get(
            "MONITORING_API_BASE_URL", "http://localhost:8000"
        )

        jwt_token = os.environ.get("MONITORING_JWT_TOKEN", "")
        if not jwt_token:
            logger.warning(
                "MONITORING_JWT_TOKEN is not set. "
                "Event sync to backend will be disabled until the token is provided."
            )
        self.JWT_TOKEN: str = jwt_token

        self.BATCH_INTERVAL_SECONDS: int = int(
            os.environ.get("MONITORING_BATCH_INTERVAL", "30")
        )
        self.RETRY_INTERVAL_SECONDS: int = int(
            os.environ.get("MONITORING_RETRY_INTERVAL", "60")
        )
        self.MAX_BATCH_SIZE: int = int(
            os.environ.get("MONITORING_MAX_BATCH_SIZE", "100")
        )


settings = MonitoringSettings()
