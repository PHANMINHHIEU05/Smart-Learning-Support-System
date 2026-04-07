import math
import time
from typing import Tuple


class FaceMeshLandmarks:
    """Constants cho MediaPipe Face Mesh landmarks (478 điểm)"""
    LEFT_EYE_OUTER = 33
    LEFT_EYE_INNER = 133
    RIGHT_EYE_OUTER = 263
    RIGHT_EYE_INNER = 362
    FOREHEAD = 10
    NOSE_TIP = 1
    CHIN = 152
    LEFT_CHEEK = 234
    RIGHT_CHEEK = 454


class PoseLandmark:
    """Constants cho MediaPipe Pose landmarks"""
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


class PostureAnalyzer:
    """Phân tích tư thế cho WEBCAM (chỉ thấy phần thân trên)
    
    Các metrics:
    - Head Pitch: Cúi/ngẩng đầu (từ Face Mesh)
    - Head Roll: Nghiêng đầu (từ Face Mesh)
    - Head Yaw: Quay trái/phải (từ Face Mesh)
    - Neck Posture: Khoảng cách mũi-vai (thay thế back curve)
    - Shoulder Angle: Vai cân bằng
    - Face Distance: Khoảng cách camera
    """
    
    def __init__(self, 
                 head_tilt_threshold: float = 20.0,
                 posture_frames: int = 8,
                 neck_threshold: float = 25.0):
        """
        Args:
            head_tilt_threshold: Góc cúi đầu tối đa (độ)
            posture_frames: Frames liên tục xấu tư thế để cảnh báo
            neck_threshold: Điểm neck posture tối thiểu (0-100)
        """
        self.head_tilt_threshold = head_tilt_threshold
        self.posture_frames = posture_frames
        self.neck_threshold = neck_threshold
        
        self.bad_posture_counter = 0
        self.is_bad_posture = False
        
        # Lưu metrics gần nhất
        self.last_neck_score = 75.0
        self.last_head_pitch = 0.0
        self.last_head_roll = 0.0
        self.last_vertical_distance = 0.0
        self.last_neck_drop = 0.0
        self.neck_baseline_distance = None
        self.face_distance_baseline = None
        self.face_baseline_start_time = None
        self.face_baseline_duration_sec = 5.0
        self.last_face_distance_raw = 0.15
        self.last_face_distance_ratio = 1.0
        self._pitch_baseline = None
        self._pitch_baseline_count = 0
        self._activity = "screen"
        self._writing_frames = 0
        self._screen_frames = 0
        self._WRITING_CONFIRM = 5
        self._SCREEN_CONFIRM = 8
        self._missing_started_at = None
        self._baseline_neck_distance = None
        self._baseline_pitch = None
        self._baseline_samples = 0
        self._BASELINE_SAMPLES_REQUIRED = 30
        self._BASELINE_DEVIATION_RATIO = 0.30
        self._MISSING_TIMEOUT_SEC = 5.0
        self.last_error_code = ""
        self.last_error_message = ""
        self.last_current_error_code = ""
        self.last_current_error_message = ""
        self.last_posture_score = 100.0
        self.last_ear_avg = 0.0

    @staticmethod
    def calculate_angle(p1, p2, p3) -> float:
        """Tính góc giữa 3 điểm"""
        v1 = [p2.x - p1.x, p2.y - p1.y]
        v2 = [p3.x - p2.x, p3.y - p2.y]
        
        dot = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        return math.degrees(math.acos(cos_angle))

    def calculate_head_tilt(self, landmarks) -> float:
        """Tính góc nghiêng đầu từ Pose landmarks"""
        nose = landmarks[PoseLandmark.NOSE]
        left_shoulder = landmarks[PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[PoseLandmark.RIGHT_SHOULDER]
        
        mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        vertical_diff = abs(nose.y - mid_shoulder_y)
        
        if nose.y > mid_shoulder_y:
            return vertical_diff * 100
        return 0

    def calculate_shoulder_angle(self, landmarks) -> float:
        """Tính góc nghiêng vai"""
        left_shoulder = landmarks[PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[PoseLandmark.RIGHT_SHOULDER]
        
        dx = right_shoulder.x - left_shoulder.x
        dy = right_shoulder.y - left_shoulder.y
        dz = (getattr(right_shoulder, "z", 0.0) or 0.0) - (
            getattr(left_shoulder, "z", 0.0) or 0.0
        )

        shoulder_dist_3d = math.sqrt(dx * dx + dy * dy + dz * dz)
        if shoulder_dist_3d == 0:
            return 0.0

        # Use 3D-normalized vertical slope so yaw/depth difference is less likely
        # to trigger a false shoulder-tilt alert.
        sin_theta = max(0.0, min(1.0, abs(dy) / shoulder_dist_3d))
        return abs(math.degrees(math.asin(sin_theta)))

    def calculate_neck_posture(self, landmarks) -> float:
        """Tính tư thế cổ/vai - THAY THẾ back curve cho webcam
        
        Nguyên lý: Khi cúi người về phía trước, khoảng cách mũi-vai GIẢM
        
        Returns:
            float: Neck score (0-100)
            - 100 = Cổ thẳng, đầu cao
            - 50 = Cúi nhẹ
            - 0 = Cúi nhiều
        """
        nose = landmarks[PoseLandmark.NOSE]
        left_shoulder = landmarks[PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[PoseLandmark.RIGHT_SHOULDER]
        
        # Trung điểm vai
        mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        
        # Khoảng cách từ mũi đến vai (theo trục Y)
        # Y trong MediaPipe: 0 = trên, 1 = dưới
        # nose.y < mid_shoulder_y = đầu cao hơn vai (tốt)
        vertical_distance = mid_shoulder_y - nose.y
        self.last_vertical_distance = float(vertical_distance)
        
        # Convert sang điểm (calibrated thresholds)
        if vertical_distance > 0.20:
            return 100.0  # Excellent - đầu rất cao
        elif vertical_distance > 0.15:
            return 85.0   # Good
        elif vertical_distance > 0.10:
            return 65.0   # OK
        elif vertical_distance > 0.05:
            return 40.0   # Cúi nhẹ
        elif vertical_distance > 0.0:
            return 20.0   # Cúi nhiều
        else:
            return 5.0    # Đầu thấp hơn vai - rất xấu

    def calculate_head_pitch(self, face_landmarks) -> float:
        """Tính góc cúi đầu từ Face Mesh

        Returns: Góc pitch (độ) - Dương = cúi, Âm = ngẩng
        """
        forehead = face_landmarks.landmark[FaceMeshLandmarks.FOREHEAD]
        chin = face_landmarks.landmark[FaceMeshLandmarks.CHIN]
        nose = face_landmarks.landmark[FaceMeshLandmarks.NOSE_TIP]

        # Robust pitch estimate for webcam: 2D face-ratio only.
        upper = math.sqrt((forehead.x - nose.x) ** 2 + (forehead.y - nose.y) ** 2)
        lower = math.sqrt((nose.x - chin.x) ** 2 + (nose.y - chin.y) ** 2)
        if lower == 0:
            return 0.0

        raw_pitch = (upper / lower - 1.0) * 35.0

        if self._pitch_baseline is None:
            self._pitch_baseline = raw_pitch
            self._pitch_baseline_count = 1
        elif self._pitch_baseline_count < 30:
            deviation = abs(raw_pitch - self._pitch_baseline)
            if deviation < 15:
                self._pitch_baseline = (
                    self._pitch_baseline * self._pitch_baseline_count + raw_pitch
                ) / (self._pitch_baseline_count + 1)
                self._pitch_baseline_count += 1
            # Nếu deviation >= 15: bỏ qua frame này

        relative_pitch = raw_pitch - (self._pitch_baseline or 0.0)
        return relative_pitch

    def calculate_head_roll(self, face_landmarks) -> float:
        """Tính góc nghiêng đầu từ Face Mesh
        
        Returns:
            float: Góc roll (độ)
            - Dương = Nghiêng sang phải
            - Âm = Nghiêng sang trái
        """
        if face_landmarks is None:
            return 0.0
            
        left_eye = face_landmarks.landmark[FaceMeshLandmarks.LEFT_EYE_OUTER]
        right_eye = face_landmarks.landmark[FaceMeshLandmarks.RIGHT_EYE_OUTER]
        
        dx = right_eye.x - left_eye.x
        dy = right_eye.y - left_eye.y
        
        # Góc so với đường ngang
        roll_angle = math.degrees(math.atan2(dy, dx))
        
        return roll_angle

    def calculate_head_yaw(self, face_landmarks) -> float:
        """Tính góc quay đầu trái/phải từ Face Mesh
        
        Returns:
            float: Góc yaw (độ)
            - Dương (+) = Quay sang phải
            - Âm (-) = Quay sang trái
        """
        if face_landmarks is None:
            return 0.0
            
        left_cheek = face_landmarks.landmark[FaceMeshLandmarks.LEFT_CHEEK]
        right_cheek = face_landmarks.landmark[FaceMeshLandmarks.RIGHT_CHEEK]
        nose = face_landmarks.landmark[FaceMeshLandmarks.NOSE_TIP]
        
        # Khoảng cách từ mũi đến má trái vs má phải
        dist_left = abs(nose.x - left_cheek.x)
        dist_right = abs(nose.x - right_cheek.x)
        
        total = dist_left + dist_right
        if total == 0:
            return 0.0
        
        # Normalize về -1 đến 1
        yaw_ratio = (dist_right - dist_left) / total
        
        # Convert sang góc (-45° đến +45°)
        yaw_angle = yaw_ratio * 45
        
        return yaw_angle

    def calculate_posture_score(self, head_tilt: float, shoulder_angle: float,
                               neck_score: float = 75.0,
                               head_pitch: float = 0.0,
                               head_roll: float = 0.0) -> float:
        """Tính điểm tư thế tổng hợp cho WEBCAM (0-100)
        
        Phân bố điểm:
        - Neck posture: 30 điểm (thay back curve)
        - Head tilt (từ pose): 25 điểm
        - Head pitch (từ face): 20 điểm
        - Shoulder alignment: 15 điểm
        - Head roll: 10 điểm
        """
        # 1. NECK POSTURE (0-30) - quan trọng nhất cho webcam
        neck_points = min(30, neck_score * 0.30)
        
        # 2. HEAD TILT from Pose (0-25)
        if head_tilt < 5:
            head_tilt_points = 25
        elif head_tilt < 10:
            head_tilt_points = 18
        elif head_tilt < 15:
            head_tilt_points = 10
        else:
            head_tilt_points = 3
        
        # 3. HEAD PITCH from Face (0-20)
        abs_pitch = abs(head_pitch)
        if abs_pitch < 15:
            pitch_points = 20
        elif abs_pitch < 25:
            pitch_points = 12
        elif abs_pitch < 40:
            pitch_points = 6
        else:
            pitch_points = 2
        
        # 4. SHOULDER ALIGNMENT (0-15)
        if shoulder_angle < 5:
            shoulder_points = 15
        elif shoulder_angle < 10:
            shoulder_points = 10
        elif shoulder_angle < 15:
            shoulder_points = 6
        else:
            shoulder_points = 2
        
        # 5. HEAD ROLL (0-10)
        abs_roll = abs(head_roll)
        if abs_roll < 5:
            roll_points = 10
        elif abs_roll < 10:
            roll_points = 6
        elif abs_roll < 15:
            roll_points = 3
        else:
            roll_points = 1
        
        total = neck_points + head_tilt_points + pitch_points + shoulder_points + roll_points
        return min(100.0, max(0.0, total))

    def _detect_activity(self, head_pitch, shoulder_angle,
                       head_yaw, neck_drop=0.0,
                       face_available=True) -> str:

        if face_available:
            is_writing_posture = (
                head_pitch > 12
                and shoulder_angle < 10
                and abs(head_yaw) < 30
            )
        else:
            is_writing_posture = (
                neck_drop > 0.03
                and shoulder_angle < 10
            )

        if is_writing_posture:
            self._writing_frames += 1
            self._screen_frames = 0
        else:
            self._screen_frames += 1
            self._writing_frames = 0

        if self._writing_frames >= self._WRITING_CONFIRM:
            self._activity = "writing"
        elif self._screen_frames >= self._SCREEN_CONFIRM:
            self._activity = "screen"

        return self._activity

    def process(self, pose_landmarks, face_landmarks=None) -> Tuple[float, float, float, bool, str]:
        """Xử lý và trả về kết quả phân tích tư thế
        
        Args:
            pose_landmarks: MediaPipe Pose landmarks
            face_landmarks: MediaPipe Face Mesh landmarks (optional, để tính head pitch/roll)
        
        Returns:
            (head_tilt, shoulder_angle, posture_score, is_bad_posture, error_message)
        """
        now = time.time()
        # Block 1: chỉ check pose_landmarks
        if pose_landmarks is None:
            if self._missing_started_at is None:
                self._missing_started_at = now
            if now - self._missing_started_at >= self._MISSING_TIMEOUT_SEC:
                self.last_error_code = "ERR_MISSING"
                self.last_error_message = "Không phát hiện người dùng, vui lòng quay lại trước webcam"
                self.is_bad_posture = True
                self.bad_posture_counter = self.posture_frames
                self.last_posture_score = 0.0
                return 0.0, 0.0, 0.0, True, self.last_error_message

            self.bad_posture_counter = max(0, self.bad_posture_counter - 1)
            if self.bad_posture_counter == 0:
                self.is_bad_posture = False
                self.last_error_code = ""
                self.last_error_message = ""
            self.last_posture_score = 100.0
            return 0.0, 0.0, 100.0, False, ""

        # Block 2: reset missing timer khi có pose
        self._missing_started_at = None
        face_available = face_landmarks is not None
            
        landmarks = pose_landmarks.landmark
        
        # 1. Từ Pose landmarks
        head_tilt = self.calculate_head_tilt(landmarks)
        shoulder_angle = self.calculate_shoulder_angle(landmarks)
        neck_score = self.calculate_neck_posture(landmarks)
        
        # 2. Từ Face Mesh
        if face_available:
            head_pitch = self.calculate_head_pitch(face_landmarks)
            head_roll = self.calculate_head_roll(face_landmarks)
            head_yaw = self.calculate_head_yaw(face_landmarks)
        else:
            head_pitch = 0.0
            head_roll = 0.0
            head_yaw = 0.0

        # 2.5. Tính head_yaw
        self.last_head_yaw = head_yaw

        # 2.6. Calibration baseline đầu phiên
        stable_pose = shoulder_angle < 10 and (
            not face_available or (abs(head_roll) < 12 and abs(head_yaw) < 25)
        )
        if stable_pose and self._baseline_samples < self._BASELINE_SAMPLES_REQUIRED:
            if self._baseline_neck_distance is None:
                self._baseline_neck_distance = self.last_vertical_distance
                if face_available:
                    self._baseline_pitch = head_pitch
            else:
                alpha = 0.1
                self._baseline_neck_distance = (
                    (1 - alpha) * self._baseline_neck_distance + alpha * self.last_vertical_distance
                )
                if face_available:
                    self._baseline_pitch = (
                        (1 - alpha) * (self._baseline_pitch if self._baseline_pitch is not None else head_pitch)
                        + alpha * head_pitch
                    )
            self._baseline_samples += 1

        self.neck_baseline_distance = self._baseline_neck_distance

        neck_drop = 0.0
        if self._baseline_neck_distance is not None:
            neck_drop = max(0.0, self._baseline_neck_distance - self.last_vertical_distance)
        self.last_neck_drop = neck_drop
        
        # Lưu lại
        self.last_neck_score = neck_score
        self.last_head_pitch = head_pitch
        self.last_head_roll = head_roll
        
        # 3. Tính tổng điểm
        posture_score = self.calculate_posture_score(
            head_tilt, shoulder_angle, neck_score, head_pitch, head_roll
        )
        self.last_posture_score = posture_score

        activity = self._detect_activity(
            head_pitch,
            shoulder_angle,
            self.last_head_yaw,
            neck_drop=self.last_neck_drop,
            face_available=face_available,
        )

        # 4. Core error detection theo rule mới
        current_frame_err = ""
        error_message = ""

        # ERR_LEANING: nghiêng đầu/nghiêng vai
        if abs(head_roll) > 15 or shoulder_angle > 10:
            current_frame_err = "ERR_LEANING"
            error_message = "Vui lòng ngồi thẳng đầu và cân bằng vai"

        # ERR_SLUMP: chỉ bắt khi đang screen, bỏ qua writing
        if not current_frame_err and activity == "screen" and self._baseline_neck_distance is not None:
            neck_drop_ratio = 0.0
            if self._baseline_neck_distance > 1e-6:
                neck_drop_ratio = (
                    (self._baseline_neck_distance - self.last_vertical_distance)
                    / self._baseline_neck_distance
                )

            left_ear = landmarks[PoseLandmark.LEFT_EAR]
            right_ear = landmarks[PoseLandmark.RIGHT_EAR]
            left_shoulder = landmarks[PoseLandmark.LEFT_SHOULDER]
            right_shoulder = landmarks[PoseLandmark.RIGHT_SHOULDER]

            left_ear_shoulder = math.sqrt(
                (left_ear.x - left_shoulder.x) ** 2 + (left_ear.y - left_shoulder.y) ** 2
            )
            right_ear_shoulder = math.sqrt(
                (right_ear.x - right_shoulder.x) ** 2 + (right_ear.y - right_shoulder.y) ** 2
            )
            min_ear_shoulder = min(left_ear_shoulder, right_ear_shoulder)

            shoulder_width = math.sqrt(
                (right_shoulder.x - left_shoulder.x) ** 2 + (right_shoulder.y - left_shoulder.y) ** 2
            )
            ear_shoulder_ratio = min_ear_shoulder / max(shoulder_width, 1e-6)

            slump_by_neck = neck_drop_ratio > self._BASELINE_DEVIATION_RATIO
            slump_by_ear = ear_shoulder_ratio < 0.52
            is_definite_slump = ear_shoulder_ratio < 0.42
            is_likely_slump = slump_by_neck and slump_by_ear
            if is_definite_slump or is_likely_slump:
                current_frame_err = "ERR_SLUMP"
                error_message = "Bạn đang cúi quá thấp, hãy nâng cổ và ngồi thẳng"

        # Pitch deviation guard theo baseline (30%) để giảm nhiễu.
        if (
            current_frame_err == "ERR_SLUMP"
            and self._baseline_pitch is not None
            and activity == "screen"
        ):
            pitch_delta = abs(head_pitch - self._baseline_pitch)
            pitch_threshold = max(abs(self._baseline_pitch) * self._BASELINE_DEVIATION_RATIO, 8.0)
            if pitch_delta < pitch_threshold:
                current_frame_err = ""
                error_message = ""

        self.last_current_error_code = current_frame_err
        self.last_current_error_message = error_message

        if current_frame_err:
            self.bad_posture_counter += 1
            if self.bad_posture_counter >= self.posture_frames:
                self.is_bad_posture = True
                self.last_error_code = current_frame_err
                self.last_error_message = error_message
        else:
            self.bad_posture_counter = max(0, self.bad_posture_counter - 1)
            if self.bad_posture_counter == 0:
                self.is_bad_posture = False
                self.last_error_code = ""
                self.last_error_message = ""

        confirmed_message = self.last_error_message if self.is_bad_posture else ""
        return head_tilt, shoulder_angle, posture_score, self.is_bad_posture, confirmed_message

    def calculate_face_distance(self, face_landmarks) -> float:
        """Ước tính khoảng cách mặt-camera qua IPD tương đối theo baseline
        
        Returns:
            float: Tỷ lệ IPD so với baseline cá nhân
            - 1.0: như khoảng cách chuẩn ban đầu
            - > 1.3: ngồi quá gần
            - < 0.75: ngồi quá xa
        """
        if face_landmarks is None:
            return self.last_face_distance_ratio
            
        left_eye = face_landmarks.landmark[FaceMeshLandmarks.LEFT_EYE_OUTER]
        right_eye = face_landmarks.landmark[FaceMeshLandmarks.RIGHT_EYE_OUTER]

        raw_ipd = math.sqrt(
            (left_eye.x - right_eye.x) ** 2 +
            (left_eye.y - right_eye.y) ** 2
        )
        self.last_face_distance_raw = raw_ipd

        now = time.time()
        if self.face_distance_baseline is None:
            self.face_distance_baseline = raw_ipd
            self.face_baseline_start_time = now
        elif (
            self.face_baseline_start_time is not None
            and (now - self.face_baseline_start_time) <= self.face_baseline_duration_sec
        ):
            # Learn stable baseline in first 5 seconds.
            self.face_distance_baseline = 0.9 * self.face_distance_baseline + 0.1 * raw_ipd
        else:
            # Slow drift adaptation to handle minor setup changes.
            self.face_distance_baseline = 0.995 * self.face_distance_baseline + 0.005 * raw_ipd

        baseline = max(self.face_distance_baseline or raw_ipd, 1e-6)
        ratio = raw_ipd / baseline
        ratio = max(0.4, min(2.5, ratio))
        self.last_face_distance_ratio = ratio
        return ratio

    def get_metrics(self) -> dict:
        """Trả về chi tiết các metrics tư thế"""
        return {
            'neck_score': round(self.last_neck_score, 1),
            'posture_score': round(self.last_posture_score, 2),
            'ear_avg': round(self.last_ear_avg, 3),
            'head_pitch': round(self.last_head_pitch, 1),
            'head_roll': round(self.last_head_roll, 1),
            'head_yaw': round(getattr(self, 'last_head_yaw', 0.0), 1),
            'neck_drop': round(self.last_neck_drop, 4),
            'neck_baseline': round(self.neck_baseline_distance, 4) if self.neck_baseline_distance is not None else None,
            'face_distance_raw_ipd': round(self.last_face_distance_raw, 4),
            'face_distance_ratio': round(self.last_face_distance_ratio, 3),
            'face_distance_baseline': round(self.face_distance_baseline, 4) if self.face_distance_baseline is not None else None,
            'is_bad_posture': self.is_bad_posture,
            'bad_counter': self.bad_posture_counter,
            'activity': self._activity,
            'writing_frames': self._writing_frames,
            'screen_frames': self._screen_frames,
            'error_code': self.last_error_code,
            'error_message': self.last_error_message,
            'current_error_code': self.last_current_error_code,
            'current_error_message': self.last_current_error_message,
            'confirmed_error': self.last_error_code if self.is_bad_posture else "",
            'baseline_pitch': round(self._baseline_pitch, 2) if self._baseline_pitch is not None else None,
            'baseline_samples': self._baseline_samples,
        }

    def get_posture_details(self) -> dict:
        """Backward-compatible alias"""
        return self.get_metrics()

    def reset(self):
        self.bad_posture_counter = 0
        self.is_bad_posture = False
        self.last_neck_score = 75.0
        self.last_head_pitch = 0.
        self.last_head_yaw = 0.00
        self.last_head_roll = 0.0
        self.last_vertical_distance = 0.0
        self.last_neck_drop = 0.0
        self.neck_baseline_distance = None
        self.face_distance_baseline = None
        self.face_baseline_start_time = None
        self.last_face_distance_raw = 0.15
        self.last_face_distance_ratio = 1.0
        self._pitch_baseline = None
        self._pitch_baseline_count = 0
        self._activity = "screen"
        self._writing_frames = 0
        self._screen_frames = 0
        self._missing_started_at = None
        self._baseline_neck_distance = None
        self._baseline_pitch = None
        self._baseline_samples = 0
        self.last_error_code = ""
        self.last_error_message = ""
        self.last_current_error_code = ""
        self.last_current_error_message = ""
        self.last_posture_score = 100.0
        self.last_ear_avg = 0.0

