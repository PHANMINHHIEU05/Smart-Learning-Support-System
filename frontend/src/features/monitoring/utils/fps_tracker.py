"""
FPS tracker utility for measuring camera processing performance.
Uses a rolling window to calculate frames per second based on frame timestamps.
"""

from collections import deque
import time


class FPSTracker:
    """Track FPS using a rolling window of frame timestamps."""

    def __init__(self, window_size: int = 30):
        """
        Initialize FPS tracker.

        Args:
            window_size: Number of frames to keep in the rolling window (default 30)
        """
        self.window_size = window_size
        self.timestamps = deque(maxlen=window_size)
        self.total_frames = 0

    def record_frame(self) -> None:
        """Record a frame completion (nanoseconds timestamp)."""
        self.timestamps.append(time.time_ns())
        self.total_frames += 1

    def get_fps(self) -> float:
        """
        Calculate FPS from rolling window of timestamps.

        Returns 0.0 if window has fewer than 2 frames (no span to measure).
        """
        if len(self.timestamps) < 2:
            return 0.0

        time_span_ns = self.timestamps[-1] - self.timestamps[0]
        time_span_s = time_span_ns / 1e9  # nanoseconds → seconds

        if time_span_s == 0:
            return 0.0

        fps = len(self.timestamps) / time_span_s
        return round(fps, 2)

    def reset(self) -> None:
        """Clear the rolling window (useful after long pauses or restarts)."""
        self.timestamps.clear()
