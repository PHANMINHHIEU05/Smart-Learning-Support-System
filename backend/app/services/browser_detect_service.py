from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

_MONITORING_ROOT = (
    Path(__file__).resolve().parents[3] 
    /"frontend"
    /"src"
    /"features"
    /"monitoring"
)
if str(_MONITORING_ROOT) not in sys.path:
    sys.path.append(str(_MONITORING_ROOT))


logger = logging.getLogger("app.browser_detect")


class BrowserDetectService:
    """phân tích frame upload tu browser va tra JSON metrics """

    def __init__(self) -> None:
        self._frame_queue = Queue(maxsize=2)
        self._result_queue = Queue(maxsize=2)
        self._ai_thread: Any | None = None
        self._start = False
        self._last_result: dict[str, Any] | None = None
        self._start_error: str | None = None
        self._analyze_calls = 0
        self._last_debug_log_at = 0.0

    def start(self) -> None:
        if self._start:
            return

        if self._start_error is not None:
            return

        if np is None or cv2 is None:
            self._start_error = "Missing numpy/cv2 in backend environment"
            logger.error("detect.start_failed reason=%s", self._start_error)
            return

        try:
            from core.ai_processor import AIProcessorThread  # type: ignore
        except Exception as exc:  # pragma: no cover
            self._start_error = f"Cannot import monitoring AI runtime: {exc}"
            logger.exception("detect.start_failed reason=%s", self._start_error)
            return

        self._ai_thread = AIProcessorThread(self._frame_queue, self._result_queue)
        self._ai_thread.start()
        self._start = True
        logger.info("detect.start_ok monitoring_root=%s", _MONITORING_ROOT)

    def _build_not_ready_payload(self, t0: float) -> dict[str, Any]:
        fps = 0.0
        if self._ai_thread is not None:
            try:
                fps = float(self._ai_thread.get_fps())
            except Exception:
                fps = 0.0

        return {
            "ready": False,
            "focus_score": 0.0,
            "confidence": 0.0,
            "state_flags": {
                "is_drowsy": False,
                "is_bad_posture": False,
                "is_distracted": False,
                "is_using_phone": False,
            },
            "overlay": {"pose_points": [], "labels": []},
            "derived_event": None,
            "detect_ms": int((time.perf_counter() - t0) * 1000),
            "server_ai_fps": fps,
        }

    @staticmethod
    def _decode_jpeg(payload: bytes):
        if np is None or cv2 is None:
            return None
        arr = np.frombuffer(payload, dtype=np.uint8)
        if arr.size == 0:
            return None
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    def analyze(self, frame_bytes: bytes) -> dict[str, Any]:
        self._analyze_calls += 1
        t0 = time.perf_counter()
        self.start()

        if self._ai_thread is None:
            return self._build_not_ready_payload(t0)

        t_decode0 = time.perf_counter()
        frame = self._decode_jpeg(frame_bytes)
        decode_ms = (time.perf_counter() - t_decode0) * 1000.0
        if frame is None:
            return self._build_not_ready_payload(t0)

        dropped_old_frame = False
        if self._frame_queue.full():
            try:
                self._frame_queue.get_nowait()
                dropped_old_frame = True
            except Empty:
                pass

        t_queue0 = time.perf_counter()
        self._frame_queue.put_nowait(frame)
        queue_put_ms = (time.perf_counter() - t_queue0) * 1000.0

        latest = self._ai_thread.get_latest_result()
        if latest is not None:
            self._last_result = latest

        data = self._last_result or {}
        focus_score = float(data.get("focus_score", 0.0) or 0.0)
        face_distance_ipd = data.get("face_distance_ipd")
        try:
            face_distance_ipd = float(face_distance_ipd) if face_distance_ipd is not None else None
        except (TypeError, ValueError):
            face_distance_ipd = None

        is_drowsy = bool(data.get("is_drowsy", False))
        is_bad_posture = bool(data.get("is_bad_posture", False))
        is_distracted = bool(data.get("is_distracted", False))
        is_using_phone = bool(data.get("is_using_phone", False))
        is_too_close = bool(face_distance_ipd is not None and face_distance_ipd > 0.20)
        is_too_far = bool(face_distance_ipd is not None and face_distance_ipd < 0.10)
        ear_avg = float(data.get("ear_avg", 0.0) or 0.0)
        posture_score = float(data.get("posture_score", 0.0) or 0.0)
        posture_details = data.get("posture_details") if isinstance(data.get("posture_details"), dict) else {}

        if is_drowsy:
            derived_event = "drowsiness"
        elif is_too_close:
            derived_event = "face_too_close"
        elif is_too_far:
            derived_event = "face_too_far"
        elif is_using_phone:
            derived_event = "phone_detected"
        elif is_bad_posture:
            derived_event = "bad_posture"
        elif is_distracted:
            derived_event = "focus_offscreen"
        else:
            derived_event = "focus_update"

        labels: list[dict[str, Any]] = [
            {
                "text": f"focus: {focus_score:.1f}",
                "x": 18,
                "y": 28,
                "severity": "soft" if focus_score >= 70 else "medium",
            }
        ]
        if is_drowsy:
            labels.append({"text": "Warning: drowsy detected", "x": 18, "y": 52, "severity": "critical"})
        if is_bad_posture:
            labels.append({"text": "Warning: bad posture", "x": 18, "y": 74, "severity": "medium"})
        if is_too_close:
            labels.append({"text": "Warning: move farther from camera", "x": 18, "y": 96, "severity": "medium"})
        if is_too_far:
            labels.append({"text": "Warning: move closer to camera", "x": 18, "y": 118, "severity": "medium"})

        overlay = {
            "pose_points": [],
            "labels": labels,
        }

        detect_ms_precise = (time.perf_counter() - t0) * 1000.0
        detect_ms_int = max(1, int(round(detect_ms_precise)))

        latest_age_ms: float | None = None
        if isinstance(data.get("timestamp"), (int, float)):
            latest_age_ms = max(0.0, (time.time() - float(data["timestamp"])) * 1000.0)

        now_mono = time.monotonic()
        if now_mono - self._last_debug_log_at >= 1.0:
            self._last_debug_log_at = now_mono
            logger.info(
                "detect.debug calls=%s ready=%s detect_ms=%.2f detect_ms_int=%s decode_ms=%.2f queue_put_ms=%.2f queue_size=%s dropped_old=%s ai_fps=%.1f latest_age_ms=%s event=%s flags={drowsy:%s,posture:%s,distracted:%s,phone:%s,close:%s,far:%s} metrics={ear_avg:%.3f,posture_score:%.1f,bad_counter:%s,neck_score:%s,head_pitch:%s} modules={face:%s,pose:%s,blend:%s} start_error=%s",
                self._analyze_calls,
                self._last_result is not None,
                detect_ms_precise,
                detect_ms_int,
                decode_ms,
                queue_put_ms,
                self._frame_queue.qsize(),
                dropped_old_frame,
                float(self._ai_thread.get_fps()),
                f"{latest_age_ms:.1f}" if latest_age_ms is not None else "none",
                derived_event,
                is_drowsy,
                is_bad_posture,
                is_distracted,
                is_using_phone,
                is_too_close,
                is_too_far,
                ear_avg,
                posture_score,
                posture_details.get("bad_counter", "none"),
                posture_details.get("neck_score", "none"),
                posture_details.get("head_pitch", "none"),
                bool(data.get("face_landmarks")),
                bool(data.get("posture_details")),
                bool(data.get("blendshapes")),
                self._start_error,
            )

        return {
            "ready": self._last_result is not None,
            "focus_score": round(focus_score, 2),
            "confidence": round(max(0.0, min(1.0, focus_score / 100.0)), 3),
            "state_flags": {
                "is_drowsy": is_drowsy,
                "is_bad_posture": is_bad_posture,
                "is_distracted": is_distracted,
                "is_using_phone": is_using_phone,
                "is_too_close": is_too_close,
                "is_too_far": is_too_far,
            },
            "overlay": overlay,
            "derived_event": derived_event,
            "detect_ms": detect_ms_int,
            "server_ai_fps": round(float(self._ai_thread.get_fps()), 1),
            "face_distance_ipd": face_distance_ipd,
        }


browser_detect_service = BrowserDetectService()


