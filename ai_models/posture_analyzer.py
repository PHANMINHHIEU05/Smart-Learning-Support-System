import math 
from typing import Tuple
import mediapipe as mp


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
                 head_tilt_threshold: float = 12.0,
                 posture_frames: int = 20,
                 neck_threshold: float = 50.0):
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
        self.mp_pose = mp.solutions.pose
        
        # Lưu metrics gần nhất
        self.last_neck_score = 75.0
        self.last_head_pitch = 0.0
        self.last_head_roll = 0.0

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
        nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        
        mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        vertical_diff = abs(nose.y - mid_shoulder_y)
        
        if nose.y > mid_shoulder_y:
            return vertical_diff * 100
        return 0

    def calculate_shoulder_angle(self, landmarks) -> float:
        """Tính góc nghiêng vai"""
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        
        dx = right_shoulder.x - left_shoulder.x
        dy = right_shoulder.y - left_shoulder.y
        
        if dx == 0:
            return 0.0
        return abs(math.degrees(math.atan(dy / dx)))

    def calculate_neck_posture(self, landmarks) -> float:
        """Tính tư thế cổ/vai - THAY THẾ back curve cho webcam
        
        Nguyên lý: Khi cúi người về phía trước, khoảng cách mũi-vai GIẢM
        
        Returns:
            float: Neck score (0-100)
            - 100 = Cổ thẳng, đầu cao
            - 50 = Cúi nhẹ
            - 0 = Cúi nhiều
        """
        nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        
        # Trung điểm vai
        mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        
        # Khoảng cách từ mũi đến vai (theo trục Y)
        # Y trong MediaPipe: 0 = trên, 1 = dưới
        # nose.y < mid_shoulder_y = đầu cao hơn vai (tốt)
        vertical_distance = mid_shoulder_y - nose.y
        
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
        """Tính góc cúi/ngẩng đầu từ Face Mesh
        
        Returns: 
            float: Góc pitch (độ)
            - Dương (+) = Cúi đầu xuống
            - Âm (-) = Ngẩng đầu lên
            - 0 = Nhìn thẳng
        """
        if face_landmarks is None:
            return 0.0
            
        forehead = face_landmarks.landmark[FaceMeshLandmarks.FOREHEAD]
        nose = face_landmarks.landmark[FaceMeshLandmarks.NOSE_TIP]
        chin = face_landmarks.landmark[FaceMeshLandmarks.CHIN]
        
        # Khoảng cách trán-mũi vs mũi-cằm
        upper = math.sqrt((forehead.x - nose.x)**2 + (forehead.y - nose.y)**2)
        lower = math.sqrt((nose.x - chin.x)**2 + (nose.y - chin.y)**2)
        
        if lower == 0:
            return 0.0
        
        # Tỷ lệ - nếu upper > lower = cúi đầu
        ratio = upper / lower
        
        # Convert sang góc (calibrated)
        pitch_angle = (ratio - 1.0) * 50
        
        return pitch_angle

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
        if abs_pitch < 10:
            pitch_points = 20
        elif abs_pitch < 20:
            pitch_points = 12
        elif abs_pitch < 30:
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

    def process(self, pose_landmarks, face_landmarks=None) -> Tuple[float, float, float, bool]:
        """Xử lý và trả về kết quả phân tích tư thế
        
        Args:
            pose_landmarks: MediaPipe Pose landmarks
            face_landmarks: MediaPipe Face Mesh landmarks (optional, để tính head pitch/roll)
        
        Returns:
            (head_tilt, shoulder_angle, posture_score, is_bad_posture)
        """
        if pose_landmarks is None:
            return 0.0, 0.0, 100.0, False
            
        landmarks = pose_landmarks.landmark
        
        # 1. Từ Pose landmarks
        head_tilt = self.calculate_head_tilt(landmarks)
        shoulder_angle = self.calculate_shoulder_angle(landmarks)
        neck_score = self.calculate_neck_posture(landmarks)
        
        # 2. Từ Face Mesh (nếu có)
        head_pitch = 0.0
        head_roll = 0.0
        if face_landmarks is not None:
            head_pitch = self.calculate_head_pitch(face_landmarks)
            head_roll = self.calculate_head_roll(face_landmarks)
        
        # Lưu lại
        self.last_neck_score = neck_score
        self.last_head_pitch = head_pitch
        self.last_head_roll = head_roll
        
        # 2.5. Tính head_yaw (nếu có face landmarks)
        head_yaw = 0.0
        if face_landmarks is not None:
            head_yaw = self.calculate_head_yaw(face_landmarks)
        self.last_head_yaw = head_yaw
        
        # 3. Tính tổng điểm
        posture_score = self.calculate_posture_score(
            head_tilt, shoulder_angle, neck_score, head_pitch, head_roll
        )
        
        # 4. Tracking bad posture
        is_bad = (posture_score < 50 or 
                 neck_score < self.neck_threshold or
                 head_tilt > self.head_tilt_threshold or
                 abs(head_pitch) > 25 or
                 abs(head_roll) > 15)
        
        if is_bad:
            self.bad_posture_counter += 1
        else:
            # Hồi phục nhanh khi tư thế tốt
            self.bad_posture_counter = max(0, self.bad_posture_counter - 2)
            self.is_bad_posture = False
            
        if self.bad_posture_counter >= self.posture_frames:
            self.is_bad_posture = True
            
        return head_tilt, shoulder_angle, posture_score, self.is_bad_posture

    def calculate_head_pitch(self, face_landmarks) -> float:
        """Tính góc cúi đầu từ Face Mesh
        
        Returns: Góc pitch (độ) - Dương = cúi, Âm = ngẩng
        """
        forehead = face_landmarks.landmark[FaceMeshLandmarks.FOREHEAD]
        chin = face_landmarks.landmark[FaceMeshLandmarks.CHIN]
        nose = face_landmarks.landmark[FaceMeshLandmarks.NOSE_TIP]
        face_height = chin.y - forehead.y
        depth_diff = chin.z - forehead.z
        
        if face_height == 0:
            return 0.0
        
        return math.degrees(math.atan2(depth_diff, abs(face_height)))

    def calculate_face_distance(self, face_landmarks) -> float:
        """Ước tính khoảng cách mặt-camera qua IPD
        
        Returns:
            float: IPD normalized (0.05-0.3)
            - > 0.2: Ngồi quá gần
            - 0.1-0.2: Bình thường
            - < 0.1: Ngồi quá xa
        """
        if face_landmarks is None:
            return 0.15
            
        left_eye = face_landmarks.landmark[FaceMeshLandmarks.LEFT_EYE_OUTER]
        right_eye = face_landmarks.landmark[FaceMeshLandmarks.RIGHT_EYE_OUTER]
        
        return math.sqrt(
            (left_eye.x - right_eye.x) ** 2 +
            (left_eye.y - right_eye.y) ** 2
        )

    def get_posture_details(self) -> dict:
        """Trả về chi tiết các metrics tư thế"""
        return {
            'neck_score': round(self.last_neck_score, 1),
            'head_pitch': round(self.last_head_pitch, 1),
            'head_roll': round(self.last_head_roll, 1),
            'head_yaw': round(getattr(self, 'last_head_yaw', 0.0), 1),
            'is_bad_posture': self.is_bad_posture,
            'bad_counter': self.bad_posture_counter
        }

    def reset(self):
        self.bad_posture_counter = 0
        self.is_bad_posture = False
        self.last_neck_score = 75.0
        self.last_head_pitch = 0.
        self.last_head_yaw = 0.00
        self.last_head_roll = 0.0

