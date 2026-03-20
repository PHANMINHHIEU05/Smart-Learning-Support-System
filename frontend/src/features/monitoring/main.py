from core.camera_thread import CameraThread
from core.ai_processor import AIProcessorThread
from ai_models.gaze_tracker import GazeTracker
from ai_models.phone_detector import PhoneDetector
from ai_models.focus_calculator import FocusCalculator
from ai_models.calibrator import Calibrator
from ai_models.adaptive_detector import AdaptiveDetector
from ai_models.advanced_state_detector import AdvancedStateDetector
# from ai_models.blendshape_emotion_mapper import BlendshapeEmotionMapper  # Đã TẮT phân tích cảm xúc
from database.db_manager import DatabaseManager
from config import performance_config as perf
from config.settings import settings as monitoring_settings
from backend_client import BackendClient
from event_sync_service import EventSyncService
import argparse
import cv2 
import os
import time
import uuid
import json
from datetime import datetime, timezone
from queue import Queue, Empty

class MainApplication:
    def __init__(self, camera_index: int = 0, no_display: bool = False):
        self.no_display = no_display
        self.snapshot_path = os.environ.get("MONITORING_SNAPSHOT_PATH")
        self.metrics_path = os.environ.get("MONITORING_METRICS_PATH")
        self.snapshot_interval = float(os.environ.get("MONITORING_SNAPSHOT_INTERVAL", "0.10"))
        self.snapshot_jpeg_quality = int(os.environ.get("MONITORING_SNAPSHOT_JPEG_QUALITY", "72"))
        self.snapshot_max_width = int(os.environ.get("MONITORING_SNAPSHOT_MAX_WIDTH", "0"))
        self.snapshot_max_height = int(os.environ.get("MONITORING_SNAPSHOT_MAX_HEIGHT", "0"))
        self.snapshot_brightness_alpha = float(
            os.environ.get("MONITORING_SNAPSHOT_BRIGHTNESS_ALPHA", "1.0")
        )
        self.snapshot_brightness_beta = float(
            os.environ.get("MONITORING_SNAPSHOT_BRIGHTNESS_BETA", "0.0")
        )
        self._last_snapshot_at = 0.0
        self.metrics_interval = float(os.environ.get("MONITORING_METRICS_INTERVAL", "0.50"))
        self._last_metrics_at = 0.0
        self.frame_queue = Queue(maxsize=perf.FRAME_QUEUE_SIZE)
        self.result_queue = Queue(maxsize=perf.RESULT_QUEUE_SIZE)
        self.camera_thread = CameraThread(camera_index, self.frame_queue)
        self.ai_thread = AIProcessorThread(self.frame_queue, self.result_queue)
        self.gaze_tracker = GazeTracker()
        self.focus_calculator = FocusCalculator()
        self.advanced_state_detector = AdvancedStateDetector()  # Phát hiện: boredom, dazed, severe distraction
        self.calibrator = Calibrator()
        # self.blendshape_mapper = BlendshapeEmotionMapper()  # ← ĐÃ TẮT phân tích cảm xúc
        self.db_manager = DatabaseManager()
        self.running = False
        self.is_calibrated = False
        self.current_focus_score = 0.0
        
        # Frame counter để skip heavy operations
        self.frame_count = 0
        self.enable_phone_detection = perf.ENABLE_PHONE_DETECTION
        self.PHONE_CHECK_INTERVAL = perf.PHONE_CHECK_INTERVAL
        self.ADVANCED_STATE_INTERVAL = perf.ADVANCED_STATE_INTERVAL  # Dùng config
        self.enable_advanced_states = perf.ENABLE_ADVANCED_STATES
        self.enable_microsleep = perf.ENABLE_MICROSLEEP
        self.phone_detector = PhoneDetector() if self.enable_phone_detection else None
        self.last_phone_result = (False, 0.0, [])
        self.last_advanced_states = {
            'is_bored': False,
            'is_dazed': False,
            'is_severely_distracted': False,
            'blink_rate': 0.0,
            'dominant_state': 'normal',
            'warning_message': ''
        }
        
        # FPS tracking
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.current_fps = 0.0

        # Backend sync — use MONITORING_SESSION_ID env var if provided (set by web timer)
        self.session_id = os.environ.get("MONITORING_SESSION_ID") or str(uuid.uuid4())
        _backend_client = BackendClient(
            base_url=monitoring_settings.API_BASE_URL,
            jwt_token=monitoring_settings.JWT_TOKEN,
        )
        self.sync_service = EventSyncService(
            client=_backend_client,
            db_manager=self.db_manager,
            settings=monitoring_settings,
        )
        self.sync_service.start()
    def start(self):
        print("Starting Main Application...")
        self.camera_thread.start()
        self.ai_thread.start()
        self.running = True
    def stop(self):
        print("Stopping Main Application...")
        self.running = False
        self.camera_thread.stop()
        self.ai_thread.stop()
        self.sync_service.stop()
        cv2.destroyAllWindows()

    def write_snapshot(self, frame) -> None:
        if not self.snapshot_path:
            return
        now = time.time()
        if now - self._last_snapshot_at < self.snapshot_interval:
            return

        snapshot_frame = frame
        if self.snapshot_max_width > 0 or self.snapshot_max_height > 0:
            h, w = snapshot_frame.shape[:2]
            max_w = self.snapshot_max_width if self.snapshot_max_width > 0 else w
            max_h = self.snapshot_max_height if self.snapshot_max_height > 0 else h
            scale = min(max_w / w, max_h / h, 1.0)
            if scale < 1.0:
                new_size = (int(w * scale), int(h * scale))
                snapshot_frame = cv2.resize(
                    snapshot_frame,
                    new_size,
                    interpolation=cv2.INTER_AREA,
                )

        if self.snapshot_brightness_alpha != 1.0 or self.snapshot_brightness_beta != 0.0:
            snapshot_frame = cv2.convertScaleAbs(
                snapshot_frame,
                alpha=self.snapshot_brightness_alpha,
                beta=self.snapshot_brightness_beta,
            )

        tmp_path = f"{self.snapshot_path}.tmp"
        ok, encoded = cv2.imencode(
            ".jpg",
            snapshot_frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.snapshot_jpeg_quality],
        )
        if not ok:
            return
        with open(tmp_path, "wb") as snapshot_file:
            snapshot_file.write(encoded.tobytes())
        os.replace(tmp_path, self.snapshot_path)
        self._last_snapshot_at = now

    def write_metrics(self, camera_fps: float, ai_fps: float) -> None:
        if not self.metrics_path:
            return
        now = time.time()
        if now - self._last_metrics_at < self.metrics_interval:
            return
        tmp_path = f"{self.metrics_path}.tmp"
        payload = {
            "main_fps": round(self.current_fps, 2),
            "camera_fps": round(camera_fps, 2),
            "ai_fps": round(ai_fps, 2),
            "updated_at": now,
        }
        with open(tmp_path, "w", encoding="utf-8") as metrics_file:
            json.dump(payload, metrics_file)
        os.replace(tmp_path, self.metrics_path)
        self._last_metrics_at = now

    def run(self):
        self.start()
        
        last_ai_result = None
        frame_interval = 1.0 / perf.DISPLAY_FPS_LIMIT  # Giới hạn FPS hiển thị
        last_frame_time = 0
        
        while self.running:
            now = time.time()
            
            # Giới hạn FPS hiển thị để không ăn CPU vô ích
            if now - last_frame_time < frame_interval:
                time.sleep(0.001)
                continue
            last_frame_time = now
            
            # === 1. LẤY FRAME MỚI NHẤT TỪ CAMERA (luôn có, không block) ===
            frame = self.camera_thread.get_latest_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            # === 2. LẤY AI RESULT MỚI NHẤT (không block, dùng cái cũ nếu chưa có mới) ===
            ai_result = self.ai_thread.get_latest_result()
            if ai_result is not None:
                last_ai_result = ai_result
            
            # === 3. XỬ LÝ & HIỂN THỊ (bỏ qua nếu chạy headless) ===
            display_frame = frame.copy()
            if not self.no_display:
                if last_ai_result is not None:
                    processed = self.process_frame(last_ai_result, frame)
                    display_frame = self.draw_overlay(frame.copy(), processed)
                else:
                    display_frame = frame.copy()
                    cv2.putText(display_frame, "Loading AI...", (20, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                self.write_metrics(self.camera_thread.get_fps(), self.ai_thread.get_fps())
                self.write_snapshot(display_frame)
                cv2.imshow("Smart Learning Support System", display_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('c'):
                    self.calibrate()
            else:
                # Headless mode: chỉ xử lý AI, không hiển thị
                if last_ai_result is not None:
                    processed = self.process_frame(last_ai_result, frame)
                    display_frame = self.draw_overlay(frame.copy(), processed)
                else:
                    cv2.putText(display_frame, "Loading AI...", (20, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                self.write_metrics(self.camera_thread.get_fps(), self.ai_thread.get_fps())
                self.write_snapshot(display_frame)
        
        self.stop()

    def calibrate(self):
        """Chạy calibration 10 giây"""
        print("🔄 Bắt đầu calibration - Giữ tư thế bình thường...")
        self.calibrator.start()
        # TODO: Implement full calibration logic
        print("✅ Calibration placeholder - cần implement đầy đủ")

    def process_frame(self, ai_result: dict, frame) -> dict:
        """Xử lý frame với tất cả AI models - TỐI ƯU PERFORMANCE"""
        self.frame_count += 1
        
        # === FPS CALCULATION ===
        self.fps_frame_count += 1
        elapsed = time.time() - self.fps_start_time
        if elapsed >= 1.0:
            self.current_fps = self.fps_frame_count / elapsed
            self.fps_frame_count = 0
            self.fps_start_time = time.time()
        
        # Lấy dữ liệu từ AI Processor
        ear_avg = ai_result.get('ear_avg', 0.25)
        posture_score = ai_result.get('posture_score', 100.0)
        face_landmarks = ai_result.get('face_landmarks', None)
        
        # === GAZE TRACKING (nhẹ - chạy mỗi frame) ===
        if face_landmarks is not None:
            gaze_ratio, gaze_dir, is_distracted = self.gaze_tracker.process(face_landmarks)
        else:
            gaze_ratio, gaze_dir, is_distracted = 0.5, "CENTER", False

        # === PHONE DETECTION (nặng - chạy theo interval) ===
        if self.enable_phone_detection and self.phone_detector is not None:
            if self.frame_count % self.PHONE_CHECK_INTERVAL == 0:
                self.last_phone_result = self.phone_detector.process(frame)
            is_using_phone, phone_confidence, _phone_detections = self.last_phone_result
        else:
            is_using_phone, phone_confidence, _phone_detections = False, 0.0, []
        
        # === EMOTION DETECTION - ĐÃ TẮT ===
        # Không phân tích cảm xúc, luôn trả về neutral để giữ compatibility với code
        emotion, emotion_conf = 'neutral', 0.0
        # === FACE DISTANCE MONITORING ===
        # IPD càng LỚN → càng GẦN camera, IPD càng NHỎ → càng XA camera
        face_distance_ipd = ai_result.get('face_distance_ipd', 0.15)
        
        if face_distance_ipd > 0.2:  # IPD LỚN = GẦN
            distance_status = "too_close"  # FIX: đổi từ "Too Far" → "too_close"
            is_too_close = True
            is_too_far = False
        elif face_distance_ipd < 0.1:  # IPD NHỎ = XA
            distance_status = "too_far"  # FIX: đổi từ "Too Close" → "too_far"
            is_too_close = False
            is_too_far = True
        else:
            distance_status = "good"
            is_too_close = False
            is_too_far = False
        
        # Ước tính khoảng cách: IPD 0.2 ≈ 35cm, 0.15 ≈ 50cm, 0.1 ≈ 75cm
        estimated_distance_cm = int(50 / (face_distance_ipd / 0.15)) if face_distance_ipd > 0 else 50
        
        
        # === ADVANCED STATE DETECTION (Boredom, Dazed, Severe Distraction) ===
        # Lấy head angles từ posture analyzer (cần cho cả advanced state và microsleep)
        posture_details = ai_result.get('posture_details', {})
        head_pitch = posture_details.get('head_pitch', 0.0)
        head_roll = posture_details.get('head_roll', 0.0)
        head_yaw = posture_details.get('head_yaw', 0.0)
        
        # Tối ưu: Chỉ chạy advanced state detection khi bật feature
        if self.enable_advanced_states:
            if self.frame_count % self.ADVANCED_STATE_INTERVAL == 0:
                advanced_states = self.advanced_state_detector.process_all_states(
                    ear_avg=ear_avg,
                    emotion=emotion,
                    emotion_conf=emotion_conf,
                    head_pitch=head_pitch,
                    head_roll=head_roll,
                    head_yaw=head_yaw,
                    gaze_direction=gaze_dir,
                    is_using_phone=is_using_phone,
                    posture_score=posture_score
                )
                # Lưu kết quả để dùng cho các frame khác
                self.last_advanced_states = advanced_states
            else:
                # Dùng kết quả cũ
                advanced_states = self.last_advanced_states
        else:
            advanced_states = {
                'is_bored': False,
                'is_dazed': False,
                'is_severely_distracted': False,
                'blink_rate': 0.0,
                'dominant_state': 'normal',
                'warning_message': ''
            }
        
        # Micro-sleep detection
        if self.enable_microsleep and self.ai_thread.drowsiness_detector is not None:
            is_microsleep, micro_duration = self.ai_thread.drowsiness_detector.detect_microsleep(
                ear_avg=ear_avg,
                head_pitch=head_pitch,
                head_yaw=head_yaw,
                head_roll=head_roll
            )
        else:
            is_microsleep, micro_duration = False, 0
        
        # === FOCUS SCORE (chỉ tập trung vào: drowsiness, posture, gaze) ===
        focus_score = self.focus_calculator.calculate_focus_score(
            ear_avg=ear_avg,
            posture_score=posture_score,
            emotion=emotion,
            gaze_ratio=gaze_ratio,
            is_distracted=is_distracted,
            is_using_phone=is_using_phone
        )
        
        processed_result = {
            **ai_result,
            'gaze_ratio': round(gaze_ratio, 3),
            'gaze_direction': gaze_dir,
            'is_distracted': is_distracted,
            'emotion': emotion,
            'emotion_confidence': round(emotion_conf, 1),
            'focus_score': focus_score,
            'focus_level': self.focus_calculator.get_focus_level(),
            'is_using_phone': is_using_phone,
            'phone_confidence': round(phone_confidence, 1),
            # Advanced states
            'advanced_states': advanced_states,
            'is_bored': advanced_states['is_bored'],
            'is_dazed': advanced_states['is_dazed'],
            'is_severely_distracted': advanced_states['is_severely_distracted'],
            'blink_rate': advanced_states['blink_rate'],
            'face_distance_ipd': face_distance_ipd,
            'distance_status': distance_status,
            'estimated_distance_cm': estimated_distance_cm,
            'is_too_close': is_too_close,
            'is_too_far': is_too_far,
            'is_microsleep': is_microsleep,
            'microsleep_duration': micro_duration
        }

        # Enqueue event for backend sync.
        # Only enqueue alert-worthy states or a periodic focus update (~1/sec at 30fps).
        is_drowsy_flag = ai_result.get('is_drowsy', False)
        is_bad_posture_flag = ai_result.get('is_bad_posture', False)
        if is_drowsy_flag or is_bad_posture_flag or is_distracted or is_using_phone or (self.frame_count % 30 == 0):
            if is_drowsy_flag:
                event_type = 'drowsiness'
            elif is_using_phone:
                event_type = 'phone_detected'
            elif is_bad_posture_flag:
                event_type = 'bad_posture'
            elif is_distracted:
                event_type = 'focus_offscreen'
            else:
                event_type = 'focus_update'
            now_iso = datetime.now(timezone.utc).isoformat()
            self.sync_service.enqueue({
                'event_type': event_type,
                'start_at': now_iso,
                'end_at': now_iso,
                'confidence': round(focus_score / 100.0, 3),
                'session_id': self.session_id,
                'payload_json': json.dumps({
                    'focus_score': focus_score,
                    'ear_avg': ear_avg,
                    'posture_score': posture_score,
                    'is_distracted': is_distracted,
                    'is_using_phone': is_using_phone,
                    'phone_confidence': round(phone_confidence, 1),
                    'distance_status': distance_status,
                }),
            })

        return processed_result

    def draw_overlay(self, frame, data: dict):
        """Vẽ thông tin lên frame"""
        h, w = frame.shape[:2]
        
        # Background cho text (làm rộng thêm cho advanced states)
        cv2.rectangle(frame, (10, 10), (420, 270), (0 , 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (420, 270), (255, 255, 255), 2)        
        focus_level = data.get('focus_level', {})
        emoji = focus_level.get('emoji', '')
        
        # Màu theo focus level
        focus_score = data.get('focus_score', 0)
        if focus_score >= 75:
            color = (0, 255, 0)  # Xanh lá
        elif focus_score >= 50:
            color = (0, 255, 255)  # Vàng
        else:
            color = (0, 0, 255)  # Đỏ
        
        # Text thông tin - TẬP TRUNG, BUỒN NGỦ, TƯ THẾ
        y = 35
        
        # Advanced states
        advanced_states = data.get('advanced_states', {})
        dominant_state = advanced_states.get('dominant_state', 'normal')
        blink_rate = advanced_states.get('blink_rate', 0.0)
        distance_cm = data.get('estimated_distance_cm', 0)
        distance_status = data.get('distance_status', 'unknown')
        if distance_status == 'too_close':
            distance_color = (0, 0, 255)
        elif distance_status == 'too_far':
            distance_color = (255 , 165, 0)
        else:
            distance_color = (0, 255, 0)
        info = [
            f"Focus: {focus_score:.1f} {emoji}",
            f"Drowsy: {'YES!' if data.get('is_drowsy') else 'NO'} (EAR: {data.get('ear_avg', 0):.3f})",
            f"Posture: {data.get('posture_score', 0):.1f} {'(BAD!)' if data.get('is_bad_posture') else '(Good)'}",
            f"Gaze: {data.get('gaze_direction', 'CENTER')} {'(Distracted!)' if data.get('is_distracted') else ''}",
            f"Phone: {'DETECTED' if data.get('is_using_phone') else 'No'} ({data.get('phone_confidence', 0):.0f}%)",
            # f"Emotion: {data.get('emotion', 'neutral')} ({data.get('emotion_confidence', 0):.0f}%)",  # ĐÃ TẮT
            f"Blink Rate: {blink_rate:.1f} blinks/min",
            f"State: {dominant_state.upper()}"
        ]
        
        for i, text in enumerate(info):
            # Focus score dùng màu đặc biệt
            text_color = color if i == 0 else (255, 255, 255)
            # Dominant state màu đỏ nếu không normal
            if i == 7 and dominant_state != 'normal':
                text_color = (0, 0, 255)
            cv2.putText(frame, text, (20, y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, text_color, 2)
            y += 26
        cv2.putText(frame, f"Distance: ~{distance_cm}cm",
           (20, y),
           cv2.FONT_HERSHEY_SIMPLEX, 0.55, distance_color, 2)
        # Cảnh báo ưu tiên cao nhất: Advanced states > Drowsy > Bad posture
        advanced_states = data.get('advanced_states', {})
        warning_msg = advanced_states.get('warning_message', '')
        if data.get('is_microsleep'):
    # Cảnh báo đỏ nhấp nháy
            if int(time.time() * 2) % 2 == 0:  # Blink effect
                cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 10)
                cv2.putText(frame, "!!! MICRO-SLEEP DETECTED !!!",
                        (w//2 - 200, h//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)

                duration_sec = data.get('microsleep_duration', 0) / 30
                cv2.putText(frame, f"Duration: {duration_sec:.1f}s",
                        (w//2 - 100, h//2 + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        elif warning_msg:  # Bored, Dazed, hoặc Severely Distracted
            cv2.putText(frame, warning_msg, (w//2 - 200, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
        elif data.get('is_too_close'):  # ← THÊM: Distance warning
            cv2.putText(frame, "TOO CLOSE TO SCREEN!", (w//2 - 180, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
        elif data.get('is_too_far'):
            cv2.putText(frame, "TOO FAR FROM CAMERA!", (w//2 - 180, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 165, 0), 3)
        elif data.get('is_drowsy'):
            cv2.putText(frame, "DROWSY WARNING!", (w//2 - 120, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        elif data.get('is_bad_posture'):
            cv2.putText(frame, "BAD POSTURE!", (w//2 - 100, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
        
        # FPS display: Main / Camera / AI
        camera_fps = self.camera_thread.get_fps()
        ai_fps = self.ai_thread.get_fps()
        cv2.putText(frame, f"FPS M/C/A: {self.current_fps:.1f}/{camera_fps:.1f}/{ai_fps:.1f}",
                    (w - 300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Phím tắt
        cv2.putText(frame, "Press 'q' to quit, 'c' to calibrate", 
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Learning Support System - Camera Monitoring")
    parser.add_argument("--no-display", action="store_true",
                        help="Run headless (no OpenCV window) — used when spawned by the web backend")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index")
    args = parser.parse_args()

    app = MainApplication(camera_index=args.camera, no_display=args.no_display)
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    finally:
        app.stop()
