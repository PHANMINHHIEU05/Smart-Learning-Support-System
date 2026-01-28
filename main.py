from core.camera_thread import CameraThread
from core.ai_processor import AIProcessorThread
from ai_models.gaze_tracker import GazeTracker
from ai_models.emotion_analyzer import EmotionAnalyzer
from ai_models.phone_detector import PhoneDetector
from ai_models.focus_calculator import FocusCalculator
from ai_models.calibrator import Calibrator
from ai_models.adaptive_detector import AdaptiveDetector
from database.db_manager import DatabaseManager
import cv2 
import time
from queue import Queue, Empty

class MainApplication:
    def __init__(self, camera_index: int = 0):
        self.frame_queue = Queue(maxsize=2)
        self.result_queue = Queue(maxsize=2)
        self.camera_thread = CameraThread(camera_index, self.frame_queue)
        self.ai_thread = AIProcessorThread(self.frame_queue, self.result_queue)
        self.gaze_tracker = GazeTracker()
        self.emotion_analyzer = EmotionAnalyzer(analysis_interval=30)  # Mỗi 30 frames
        # Phone detector: giảm phone_frames vì check mỗi 3 frame
        self.phone_detector = PhoneDetector(confidence_threshold=0.35, phone_frames=5)
        self.focus_calculator = FocusCalculator()
        self.calibrator = Calibrator()
        self.db_manager = DatabaseManager()
        self.running = False
        self.is_calibrated = False
        self.current_focus_score = 0.0
        
        # Frame counter để skip heavy operations
        self.frame_count = 0
        self.PHONE_CHECK_INTERVAL = 2  # Check phone mỗi 2 frames (nhanh hơn)
        self.last_phone_result = (False, 0.0, [])
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
        cv2.destroyAllWindows()
    def run(self):
        self.start()
        while self.running:
            try:
                result = self.result_queue.get(timeout=0.1)
                frame = result['frame']
                processed = self.process_frame(result, frame)
                display_frame = self.draw_overlay(frame, processed)
                cv2.imshow("Smart Learning Support System", display_frame)
            except Empty:
                pass
            
            # Xử lý phím bấm (luôn chạy)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.calibrate()
        
        self.stop()

    def calibrate(self):
        """Chạy calibration 10 giây"""
        print("🔄 Bắt đầu calibration - Giữ tư thế bình thường...")
        self.calibrator.start()
        # TODO: Implement full calibration logic
        print("✅ Calibration placeholder - cần implement đầy đủ")

    def process_frame(self, ai_result: dict, frame) -> dict:
        """Xử lý frame với tất cả AI models"""
        self.frame_count += 1
        
        # Lấy dữ liệu từ AI Processor
        ear_avg = ai_result.get('ear_avg', 0.25)
        posture_score = ai_result.get('posture_score', 100.0)
        face_landmarks = ai_result.get('face_landmarks', None)
        
        # === GAZE TRACKING ===
        if face_landmarks is not None:
            gaze_ratio, gaze_dir, is_distracted = self.gaze_tracker.process(face_landmarks)
        else:
            gaze_ratio, gaze_dir, is_distracted = 0.5, "CENTER", False
        
        # === EMOTION ANALYSIS (mỗi 30 frames) ===
        emotion, emotion_conf, _ = self.emotion_analyzer.analyze(frame)
        
        # === PHONE DETECTION (mỗi 2 frames để tăng tốc) ===
        if self.frame_count % self.PHONE_CHECK_INTERVAL == 0:
            # Dùng frame gốc để detection chính xác hơn
            is_using_phone, phone_conf, phone_dets = self.phone_detector.process(frame)
            self.last_phone_result = (is_using_phone, phone_conf, phone_dets)
        else:
            is_using_phone, phone_conf, phone_dets = self.last_phone_result
        
        # === FOCUS SCORE ===
        focus_score = self.focus_calculator.calculate_focus_score(
            ear_avg=ear_avg,
            posture_score=posture_score,
            emotion=emotion,
            gaze_ratio=gaze_ratio,
            is_distracted=is_distracted,
            is_using_phone=is_using_phone
        )
        
        return {
            **ai_result,
            'gaze_ratio': round(gaze_ratio, 3),
            'gaze_direction': gaze_dir,
            'is_distracted': is_distracted,
            'emotion': emotion,
            'emotion_confidence': round(emotion_conf, 1),
            'is_using_phone': is_using_phone,
            'phone_confidence': round(phone_conf, 2),
            'focus_score': focus_score,
            'focus_level': self.focus_calculator.get_focus_level()
        }
    def draw_overlay(self, frame, data: dict):
        """Vẽ thông tin lên frame"""
        h, w = frame.shape[:2]
        
        # Background cho text (làm rộng hơn)
        cv2.rectangle(frame, (10, 10), (350, 220), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (350, 220), (255, 255, 255), 2)
        
        # Lấy focus level
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
        
        # Text thông tin
        y = 35
        info = [
            f"Focus: {focus_score:.1f} {emoji}",
            f"EAR: {data.get('ear_avg', 0):.3f} {'(Drowsy!)' if data.get('is_drowsy') else ''}",
            f"Emotion: {data.get('emotion', 'neutral')} ({data.get('emotion_confidence', 0):.0f}%)",
            f"Gaze: {data.get('gaze_direction', 'CENTER')} ({data.get('gaze_ratio', 0.5):.2f})",
            f"Phone: {'YES!' if data.get('is_using_phone') else 'NO'} ({data.get('phone_confidence', 0):.0f}%)",
            f"Posture: {data.get('posture_score', 0):.1f}",
            f"Distracted: {'YES' if data.get('is_distracted') else 'NO'}"
        ]
        
        for i, text in enumerate(info):
            # Focus score dùng màu đặc biệt
            text_color = color if i == 0 else (255, 255, 255)
            cv2.putText(frame, text, (20, y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, text_color, 2)
            y += 26
        
        # Vẽ box phone nếu detected
        if data.get('is_using_phone'):
            cv2.putText(frame, "PHONE DETECTED!", (w//2 - 100, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        
        # Phím tắt
        cv2.putText(frame, "Press 'q' to quit, 'c' to calibrate", 
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
if __name__ == "__main__":
    app = MainApplication(camera_index=0)
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    finally:
        app.stop()