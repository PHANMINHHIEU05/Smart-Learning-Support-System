import cv2 
import threading
import time
import os
from queue import Queue, Empty
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import Optional, Dict
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import performance_config as perf
from ai_models.drowsiness_detector import DrowsinessDetector
from ai_models.posture_analyzer import PostureAnalyzer
from ai_models.focus_calculator import FocusCalculator
from ai_models.calibrator import Calibrator
from ai_models.user_profile import UserProfile
from utils.fps_tracker import FPSTracker

_MONITORING_ROOT = Path(__file__).resolve().parents[1]
_MODEL_FACE_PATH = str(_MONITORING_ROOT / "models" / "face_landmarker.task")
_MODEL_POSE_PATH = str(_MONITORING_ROOT / "models" / "pose_landmarker_lite.task")
_USER_PROFILE_PATH = str(_MONITORING_ROOT / "data" / "user_profile.json")


class AIProcessorThread(threading.Thread):
    """Thread xử lý AI: Face Mesh + Pose detection"""
    
    def __init__(self, frame_queue: Queue, result_queue: Queue):
        super().__init__()
        self.daemon = True
        self.frame_queue = frame_queue
        self.result_queue = result_queue

        self.running = False
        self.face_landmarker = None
        self.pose_landmarker = None

        self.drowsiness_detector = None
        self.posture_analyzer = None
        self.focus_calculator = None
        self.calibrator = None
        self.user_profile = None
        self.auto_calibrating = False
        
        self.current_emotion = 'neutral'
        self.emotion_confidence = 0.0
        self.EMOTION_UPDATE_INTERVAL = 30
        self.emotion_frame_count = 0

        self.fps = 0.0
        self.frame_count = 0
        self.start_time = None
        
        # Frame skipping and caching for performance
        self.cached_result = None
        self.processing_frame_count = 0
        
        # FPS tracking (rolling 30-frame window)
        self.fps_tracker = FPSTracker(window_size=30)
        
        # Thread-safe latest result cho main thread
        self._latest_result = None
        self._result_lock = threading.Lock()
        
        # Monotonic timestamp counter cho VIDEO mode (tránh lỗi tracking)
        self._timestamp_counter = 0
        self._timestamp_interval_ms = 33  # ~30fps interval

    def get_latest_result(self):
        """Lấy AI result mới nhất - thread-safe, không block"""
        with self._result_lock:
            return self._latest_result

    def get_python_fps(self) -> float:
        """Get current Python FPS from rolling window."""
        return self.fps_tracker.get_fps()

    def request_recalibration(self, clear_saved_profile: bool = True) -> bool:
        """Reset personal profile and start calibration on next frames."""
        if self.calibrator is None:
            return False

        if clear_saved_profile:
            try:
                if os.path.exists(_USER_PROFILE_PATH):
                    os.remove(_USER_PROFILE_PATH)
            except Exception:
                pass

        self.user_profile = None
        self.auto_calibrating = True
        self.calibrator.start()
        print("🔄 Nhận lệnh re-calibration: vui lòng ngồi đúng tư thế trong 10 giây")
        return True

    def get_calibration_status(self) -> Dict:
        """Runtime calibration status for API sync endpoints."""
        profile_ready = bool(self.user_profile is not None and self.user_profile.is_calibrated)
        progress = 0.0
        if self.calibrator is not None:
            progress = float(self.calibrator.progress * 100.0)
        if not self.auto_calibrating and profile_ready:
            progress = 100.0

        progress = max(0.0, min(100.0, progress))
        return {
            "is_calibrating": bool(self.auto_calibrating),
            "calibration_progress": round(progress, 1),
            "profile_ready": profile_ready,
        }

    def _init_models(self) -> bool:
        try:
            print("🔄 Đang khởi tạo AI models...")

            # === MEDIAPIPE FACE LANDMARKER với BLENDSHAPES ===
            face_base_options = python.BaseOptions(
                model_asset_path=_MODEL_FACE_PATH
            )

            face_options = vision.FaceLandmarkerOptions(
                base_options=face_base_options,
                output_face_blendshapes=perf.ENABLE_BLENDSHAPES,  # ← Dùng config flag
                output_facial_transformation_matrixes=False,
                num_faces=perf.FACE_NUM_FACES,
                min_face_detection_confidence=perf.FACE_DETECTION_CONFIDENCE,
                min_face_presence_confidence=perf.FACE_PRESENCE_CONFIDENCE,
                min_tracking_confidence=perf.FACE_TRACKING_CONFIDENCE,
                running_mode=vision.RunningMode.VIDEO  # VIDEO mode cho tracking tốt hơn
            )

            self.face_landmarker = vision.FaceLandmarker.create_from_options(face_options)

            # === MEDIAPIPE POSE LANDMARKER (Tasks API) - CHỈ NẾU ENABLE ===
            if perf.ENABLE_POSE_DETECTION:
                pose_base_options = python.BaseOptions(
                    model_asset_path=_MODEL_POSE_PATH
                )

                pose_options = vision.PoseLandmarkerOptions(
                    base_options=pose_base_options,
                    running_mode=vision.RunningMode.VIDEO,  # VIDEO mode
                    min_pose_detection_confidence=perf.POSE_DETECTION_CONFIDENCE,
                    min_pose_presence_confidence=perf.POSE_PRESENCE_CONFIDENCE,
                    min_tracking_confidence=perf.POSE_TRACKING_CONFIDENCE
                )

                self.pose_landmarker = vision.PoseLandmarker.create_from_options(pose_options)
            else:
                self.pose_landmarker = None
                print("⚠️  Pose detection đã tắt để tăng FPS")
            self.drowsiness_detector = DrowsinessDetector()
            self.posture_analyzer = PostureAnalyzer()
            self.focus_calculator = FocusCalculator()
            self.calibrator = Calibrator(duration=10.0)
            self.user_profile = UserProfile.load_from_file(_USER_PROFILE_PATH)

            if self.user_profile is None or not self.user_profile.is_calibrated:
                self.auto_calibrating = True
                self.calibrator.start()
                print("ℹ️  Chưa có profile cá nhân: bắt đầu auto-calibration (10s, ngồi thẳng)")
            else:
                self.auto_calibrating = False
                print("✅ Đã tải profile cá nhân để giám sát theo baseline riêng")
            
            if perf.ENABLE_BLENDSHAPES:
                print("✅ AI models khởi tạo thành công (với Blendshapes!)")
            elif perf.ENABLE_POSE_DETECTION:
                print("✅ AI models khởi tạo thành công (không Blendshapes)")
            else:
                print("✅ AI models khởi tạo thành công (chỉ Face detection - MAX FPS!)")
            return True
        except Exception as e:
            print(f"❌ Lỗi khởi tạo AI models: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _process_frame(self, frame) -> Optional[Dict]:
        try:
            self.processing_frame_count += 1
            
            # FRAME SKIPPING: Chỉ process mỗi N frames (nếu bật)
            if perf.ENABLE_FRAME_SKIPPING:
                should_process_face = (self.processing_frame_count % perf.FACE_PROCESS_INTERVAL == 0)
                should_process_pose = (
                    perf.ENABLE_POSE_DETECTION and
                    (self.processing_frame_count % perf.POSE_PROCESS_INTERVAL == 0)
                )
            else:
                should_process_face = True
                should_process_pose = perf.ENABLE_POSE_DETECTION
            
            # Nếu cả 2 đều skip, dùng cached result
            if (
                perf.ENABLE_RESULT_CACHING and
                not should_process_face and
                not should_process_pose and
                self.cached_result
            ):
                cached = self.cached_result.copy()
                cached['frame'] = frame  # Update frame mới
                cached['timestamp'] = time.time()
                return cached
            
            # Smart resize - chỉ resize 1 lần với config
            if perf.ENABLE_SMART_RESIZE:
                frame_small = cv2.resize(frame, 
                                        (perf.PROCESSING_WIDTH, perf.PROCESSING_HEIGHT),
                                        interpolation=cv2.INTER_LINEAR)
            else:
                h, w = frame.shape[:2]
                scale = 320 / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                frame_small = cv2.resize(frame, (new_w, new_h))

            # Convert BGR → RGB cho MediaPipe
            frame_rgb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)

            # === FACE LANDMARKER (API mới) ===
            # Phải convert sang MediaPipe Image format
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=frame_rgb
            )
            
            # Timestamp monotonic cho VIDEO mode (phải luôn tăng đều)
            self._timestamp_counter += self._timestamp_interval_ms
            timestamp_ms = self._timestamp_counter

            # Extract landmarks và blendshapes
            face_landmarks = None
            blendshapes_dict = {}
            
            if should_process_face:
                # Detect face + blendshapes
                face_result = self.face_landmarker.detect_for_video(mp_image, timestamp_ms)

                if face_result.face_landmarks and len(face_result.face_landmarks) > 0:
                    # Landmarks (để tương thích với code cũ)
                    face_landmarks = self._convert_landmarks(face_result.face_landmarks[0])

                    # Blendshapes - Selective nếu enable
                    if face_result.face_blendshapes and len(face_result.face_blendshapes) > 0:
                        blendshapes_list = face_result.face_blendshapes[0]
                        if perf.USE_SELECTIVE_BLENDSHAPES:
                            # Chỉ lấy blendshapes quan trọng
                            blendshapes_dict = {
                                bs.category_name: bs.score
                                for bs in blendshapes_list
                                if bs.category_name in perf.IMPORTANT_BLENDSHAPES
                            }
                        else:
                            # Lấy tất cả
                            blendshapes_dict = {
                                bs.category_name: bs.score
                                for bs in blendshapes_list
                            }
            elif self.cached_result:
                # Dùng face data từ cache
                face_landmarks = self.cached_result.get('face_landmarks')
                blendshapes_dict = self.cached_result.get('blendshapes', {})

            # === POSE DETECTION (Tasks API) ===
            pose_landmarks = None
            if should_process_pose and perf.ENABLE_POSE_DETECTION and self.pose_landmarker:
                pose_result = self.pose_landmarker.detect_for_video(mp_image, timestamp_ms)
                
                # Convert pose landmarks sang format cũ để tương thích
                if pose_result.pose_landmarks and len(pose_result.pose_landmarks) > 0:
                    pose_landmarks = self._convert_landmarks(pose_result.pose_landmarks[0])
            elif self.cached_result:
                # Dùng pose data từ cache (nhưng không lưu trong cached_result, tính lại)
                pass

            # === XỬ LÝ TIẾP (giữ nguyên phần drowsiness, posture...) ===
            ear_left, ear_right, is_drowsy = 0.0, 0.0, False
            if face_landmarks is not None:
                ear_left, ear_right, is_drowsy = self.drowsiness_detector.process(face_landmarks)
            ear_avg = (ear_left + ear_right) / 2.0

            # Posture analysis
            head_tilt, shoulder_angle, posture_score, is_bad_posture = 0.0, 0.0, 100.0, False
            if pose_landmarks:
                head_tilt, shoulder_angle, posture_score, is_bad_posture = \
                    self.posture_analyzer.process(pose_landmarks, face_landmarks)

            # Face distance
            face_distance_ipd = 0.15
            if face_landmarks is not None:
                face_distance_ipd = self.posture_analyzer.calculate_face_distance(face_landmarks)

            posture_details = self.posture_analyzer.get_posture_details()

            # Personalized posture refinement from calibrated user profile.
            if self.user_profile is not None and self.user_profile.is_calibrated:
                head_pitch = float(posture_details.get('head_pitch', 0.0) or 0.0)
                profile_bad = self.user_profile.is_bad_posture(
                    current_head_tilt=head_tilt,
                    current_shoulder_angle=shoulder_angle,
                    threshold=2.2,
                ) or self.user_profile.is_head_down(
                    current_pitch=head_pitch,
                    threshold=2.2,
                )
                if profile_bad:
                    is_bad_posture = True

            # Auto calibration flow: collect stable baseline samples in first seconds.
            if self.auto_calibrating and self.calibrator is not None and face_landmarks is not None:
                self.calibrator.add_sample(
                    ear_avg=ear_avg,
                    head_tilt=head_tilt,
                    shoulder_angle=shoulder_angle,
                    distance=face_distance_ipd,
                    head_pitch=float(posture_details.get('head_pitch', 0.0) or 0.0),
                    ipd=face_distance_ipd,
                )
                if self.calibrator.is_complete():
                    profile = self.calibrator.finish()
                    if profile is not None:
                        profile.save_to_file(_USER_PROFILE_PATH)
                        self.user_profile = profile
                        print("✅ Đã tạo profile cá nhân mới cho giám sát tư thế")
                    self.auto_calibrating = False

                # During calibration we avoid posture alerts to reduce false positives.
                is_bad_posture = False

            focus_score = self.focus_calculator.calculate_focus_score(
                ear_avg=ear_avg,
                posture_score=posture_score,
                emotion=self.current_emotion
            )

            calibration_state = self.get_calibration_status()

            result = {
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
                'is_calibrating': calibration_state['is_calibrating'],
                'calibration_progress': calibration_state['calibration_progress'],
                'profile_ready': calibration_state['profile_ready'],
                'face_landmarks': face_landmarks,
                'blendshapes': blendshapes_dict,  # ← THÊM MỚI
                'frame': frame
            }
            
            # Cache result cho lần sau
            if perf.ENABLE_RESULT_CACHING:
                self.cached_result = result.copy()
            
            # Record frame completion for FPS tracking
            self.fps_tracker.record_frame()
            
            return result
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
                
                if result:
                    # Lưu latest result cho main thread (luôn có sẵn)
                    with self._result_lock:
                        self._latest_result = result
                    
                    # Vẫn put vào queue cho backward compat
                    if not self.result_queue.full():
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
        if self.face_landmarker:
            self.face_landmarker.close()
        if self.pose_landmarker:
            self.pose_landmarker.close()

    def get_fps(self) -> float:
        return self.fps
