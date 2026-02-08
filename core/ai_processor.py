import cv2 
import threading
import time
from queue import Queue, Empty
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
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

            # === MEDIAPIPE FACE LANDMARKER với BLENDSHAPES ===
            base_options = python.BaseOptions(
                model_asset_path='models/face_landmarker.task'
            )

            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=True,  # ← KEY: Bật blendshapes!
                output_facial_transformation_matrixes=False,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )

            self.face_landmarker = vision.FaceLandmarker.create_from_options(options)

            # === MEDIAPIPE POSE (giữ nguyên) ===
            # Import solutions cho Pose (vì Tasks API chưa có Pose)
            import mediapipe as mp
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                model_complexity=0,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                enable_segmentation=False
            )
            self.drowsiness_detector = DrowsinessDetector()
            self.posture_analyzer = PostureAnalyzer()
            self.focus_calculator = FocusCalculator()
            print("✅ AI models khởi tạo thành công (với Blendshapes!)")
            return True
        except Exception as e:
            print(f"❌ Lỗi khởi tạo AI models: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _process_frame(self, frame) -> Optional[Dict]:
        try:
            # Resize frame cho processing
            h, w = frame.shape[:2]
            scale = 320 / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            frame_small = cv2.resize(frame, (new_w, new_h))

            # Convert BGR → RGB cho MediaPipe
            frame_rgb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)

            # === FACE LANDMARKER (API mới) ===
            # Phải convert sang MediaPipe Image format
            mp_image = python.vision.Image(
                image_format=python.vision.ImageFormat.SRGB,
                data=frame_rgb
            )

            # Detect face + blendshapes
            face_result = self.face_landmarker.detect(mp_image)

            # Extract landmarks và blendshapes
            face_landmarks = None
            blendshapes_dict = {}

            if face_result.face_landmarks and len(face_result.face_landmarks) > 0:
                # Landmarks (để tương thích với code cũ)
                # MediaPipe Tasks trả về list, cần convert sang format cũ
                face_landmarks = self._convert_landmarks(face_result.face_landmarks[0])

                # Blendshapes
                if face_result.face_blendshapes and len(face_result.face_blendshapes) > 0:
                    blendshapes_list = face_result.face_blendshapes[0]
                    # Convert thành dict: {'mouthSmileLeft': 0.8, ...}
                    blendshapes_dict = {
                        bs.category_name: bs.score
                        for bs in blendshapes_list
                    }

            # === POSE DETECTION (giữ nguyên) ===
            pose_results = self.pose.process(frame_rgb)

            # === XỬ LÝ TIẾP (giữ nguyên phần drowsiness, posture...) ===
            ear_left, ear_right, is_drowsy = 0.0, 0.0, False
            if face_landmarks is not None:
                ear_left, ear_right, is_drowsy = self.drowsiness_detector.process(face_landmarks)
            ear_avg = (ear_left + ear_right) / 2.0

            # Posture analysis
            head_tilt, shoulder_angle, posture_score, is_bad_posture = 0.0, 0.0, 100.0, False
            if pose_results.pose_landmarks:
                head_tilt, shoulder_angle, posture_score, is_bad_posture = \
                    self.posture_analyzer.process(pose_results.pose_landmarks, face_landmarks)

            # Face distance
            face_distance_ipd = 0.15
            if face_landmarks is not None:
                face_distance_ipd = self.posture_analyzer.calculate_face_distance(face_landmarks)

            posture_details = self.posture_analyzer.get_posture_details()

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
                'face_distance_ipd': round(face_distance_ipd, 3),
                'posture_details': posture_details,
                'emotion': self.current_emotion,
                'emotion_confidence': round(self.emotion_confidence, 2),
                'focus_score': focus_score,
                'is_drowsy': is_drowsy,
                'is_bad_posture': is_bad_posture,
                'face_landmarks': face_landmarks,
                'blendshapes': blendshapes_dict,  # ← THÊM MỚI
                'frame': frame
            }
        except Exception as e:
            print(f"❌ Lỗi xử lý frame: {e}")
            import traceback
            traceback.print_exc()
            return None 
    def _convert_landmarks(self, new_landmarks) :
        class LandmarkList:
            def __init__(self, landmarks):
                self.landmark = landmarks
        class Landmark:
            def __init__(self, x, y, z):
                self.x = x
                self.y = y
                self.z = z
        converted = [
            Landmark(lm.x, lm.y, lm.z)
            for lm in new_landmarks
        ]
        return LandmarkList(converted)

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
