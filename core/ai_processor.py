import cv2 
import threading
import time
import mediapipe as mp
from queue import Queue, Empty
from typing import Optional, Dict

from ai_models.drowsiness_detector import DrowsinessDetector
from ai_models.posture_analyzer import PostureAnalyzer
from ai_models.focus_calculator import FocusCalculator


class AIProcessorThread(threading.Thread):
    """Thread xử lý AI: Face Mesh + Pose detection"""
    
    def __init__(self, frame_queue: Queue, result_queue: Queue):
        super().__init__()
        self.daemon = True
        self.frame_queue = frame_queue
        self.result_queue = result_queue

        self.running = False
        self.mp_face_mesh = None
        self.mp_pose = None
        self.face_mesh = None
        self.pose = None

        self.drowsiness_detector = None
        self.posture_analyzer = None
        self.focus_calculator = None
        
        self.current_emotion = 'neutral'
        self.emotion_confidence = 0.0
        self.EMOTION_UPDATE_INTERVAL = 30
        self.emotion_frame_count = 0

        self.fps = 0.0
        self.frame_count = 0
        self.start_time = None

    def _init_models(self) -> bool:
        try:
            print("🔄 Đang khởi tạo AI models...")
            
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            self.drowsiness_detector = DrowsinessDetector()
            self.posture_analyzer = PostureAnalyzer()
            self.focus_calculator = FocusCalculator()
            
            print("✅ AI models khởi tạo thành công")
            return True
        except Exception as e:
            print(f"❌ Lỗi khởi tạo AI models: {e}")
            return False

    def _process_frame(self, frame) -> Optional[Dict]:
        try:
            # Resize để tăng tốc
            frame_small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            frame_rgb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
            
            face_results = self.face_mesh.process(frame_rgb)
            pose_results = self.pose.process(frame_rgb)
            
            # Drowsiness detection
            ear_left, ear_right, is_drowsy = 0.0, 0.0, False
            if face_results.multi_face_landmarks:
                face_landmarks = face_results.multi_face_landmarks[0]
                ear_left, ear_right, is_drowsy = self.drowsiness_detector.process(face_landmarks)
            ear_avg = (ear_left + ear_right) / 2.0
            
            # Posture analysis
            head_tilt, shoulder_angle, posture_score, is_bad_posture = 0.0, 0.0, 100.0, False
            if pose_results.pose_landmarks:
                head_tilt, shoulder_angle, posture_score, is_bad_posture = \
                    self.posture_analyzer.process(pose_results.pose_landmarks)
            
            # Focus score
            focus_score = self.focus_calculator.calculate_focus_score(
                ear_avg=ear_avg,
                posture_score=posture_score,
                emotion=self.current_emotion
            )

            return {
                'timestamp': time.time(),
                'ear_left': round(ear_left, 3),
                'ear_right': round(ear_right, 3),
                'ear_avg': round(ear_avg, 3),
                'head_tilt': round(head_tilt, 2),
                'shoulder_angle': round(shoulder_angle, 2),
                'posture_score': round(posture_score, 2),
                'emotion': self.current_emotion,
                'emotion_confidence': round(self.emotion_confidence, 2),
                'focus_score': focus_score,
                'is_drowsy': is_drowsy,
                'is_bad_posture': is_bad_posture,
                'frame': frame
            }
        except Exception as e:
            print(f"❌ Lỗi xử lý frame: {e}")
            return None

    def run(self):
        if not self._init_models():
            return
        
        self.running = True
        self.start_time = time.time()
        print("✅ AI Processor Thread đã khởi động")
        
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1)
                result = self._process_frame(frame)
                
                if result and not self.result_queue.full():
                    self.result_queue.put(result)
                
                # Tính FPS
                self.frame_count += 1
                elapsed = time.time() - self.start_time
                if elapsed >= 1.0:
                    self.fps = self.frame_count / elapsed
                    self.frame_count = 0
                    self.start_time = time.time()
                    
            except Empty:
                continue
            except Exception as e:
                print(f"❌ Lỗi AI Processor: {e}")
        
        self._cleanup()
        print("🛑 AI Processor Thread đã dừng")

    def stop(self):
        self.running = False

    def _cleanup(self):
        if self.face_mesh:
            self.face_mesh.close()
        if self.pose:
            self.pose.close()

    def get_fps(self) -> float:
        return self.fps
