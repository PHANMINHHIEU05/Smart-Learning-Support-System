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
    def __init__(self, camera_index :int  = 0):
        self.frame_queue = Queue(maxsize= 2)
        self.result_queue = Queue(maxsize= 2)
        self.camera_thread = CameraThread(camera_index, self.frame_queue)
        self.ai_thread = AIProcessorThread(self.frame_queue, self.result_queue)
        self.gaze_tracker = GazeTracker()
        self.emotion_analyzer = EmotionAnalyzer(analysis_interval=30)
        self.phone_detector = PhoneDetector()
        self.focus_calculator = FocusCalculator()
        self.calibrator = Calibrator()
        self.db_manager = DatabaseManager()
        self.running = False
        self.is_calibrated = False
        self.current_focus_score = 0.0
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
        ear_avg = ai_result.get('ear_avg', 0.25)
        posture_score = ai_result.get('posture_score', 100.0)
        gaze_ratio, gaze_dir, is_distracted = 0.5 , "CENTER" , False
        emotion, emotion_conf, _ = self.emotion_analyzer.analyze(frame)
        is_using_phone, phone_conf, phone_dets = self.phone_detector.process(frame)
        focus_score = self.focus_calculator.calculate_focus_score(
            ear_avg= ear_avg,
            posture_score= posture_score,
            emotion= emotion,
            gaze_ratio= gaze_ratio,
            is_distracted= is_distracted,
            is_using_phone= is_using_phone
        )
        return {
            **ai_result,
            'gaze_ratio': gaze_ratio,
            'gaze_direction': gaze_dir,
            'is_distracted': is_distracted,
            'emotion': emotion,
            'emotion_confidence': emotion_conf,
            'is_using_phone': is_using_phone,
            'focus_score': focus_score,
            'focus_level': self.focus_calculator.get_focus_level()
        }
    def draw_overlay(self, frame, data: dict):
        """Vẽ thông tin lên frame"""
        h, w = frame.shape[:2]
        
        # Background cho text
        cv2.rectangle(frame, (10, 10), (300, 200), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (300, 200), (255, 255, 255), 2)
        
        # Text thông tin
        y = 35
        info = [
            f"Focus: {data.get('focus_score', 0):.1f} {data.get('focus_level', {}).get('emoji', '')}",
            f"EAR: {data.get('ear_avg', 0):.3f}",
            f"Emotion: {data.get('emotion', 'neutral')}",
            f"Gaze: {data.get('gaze_direction', 'CENTER')}",
            f"Phone: {'YES' if data.get('is_using_phone') else 'NO'}",
            f"Posture: {data.get('posture_score', 0):.1f}"
        ]
        
        for text in info:
            cv2.putText(frame, text, (20, y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y += 25
        
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