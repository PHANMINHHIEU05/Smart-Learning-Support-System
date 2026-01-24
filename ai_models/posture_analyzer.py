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
    """Phân tích tư thế từ Pose và Face Mesh landmarks"""
    
    def __init__(self, head_tilt_threshold: float = 15.0, posture_frames: int = 30):
        self.head_tilt_threshold = head_tilt_threshold
        self.posture_frames = posture_frames
        self.bad_posture_counter = 0
        self.is_bad_posture = False
        self.mp_pose = mp.solutions.pose

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

    def calculate_posture_score(self, head_tilt: float, shoulder_angle: float) -> float:
        """Tính điểm tư thế tổng hợp (0-100)"""
        if head_tilt < 5:
            head_score = 100
        elif head_tilt < 15:
            head_score = 80
        else:
            head_score = 10
            
        if shoulder_angle < 5:
            shoulder_score = 50
        elif shoulder_angle < 15:
            shoulder_score = 30
        else:
            shoulder_score = 10
            
        return head_score + shoulder_score

    def process(self, pose_landmarks) -> Tuple[float, float, float, bool]:
        """Xử lý Pose landmarks và trả về kết quả phân tích tư thế"""
        if pose_landmarks is None:
            return 0.0, 0.0, 100, False
            
        landmarks = pose_landmarks.landmark
        head_tilt = self.calculate_head_tilt(landmarks)
        shoulder_angle = self.calculate_shoulder_angle(landmarks)
        posture_score = self.calculate_posture_score(head_tilt, shoulder_angle)
        
        if head_tilt > self.head_tilt_threshold or shoulder_angle < 20:
            self.bad_posture_counter += 1
        else:
            self.bad_posture_counter = 0
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
        
        face_height = chin.y - forehead.y
        depth_diff = chin.z - forehead.z
        
        if face_height == 0:
            return 0.0
        
        return math.degrees(math.atan2(depth_diff, abs(face_height)))

    def calculate_face_distance(self, face_landmarks) -> float:
        """Ước tính khoảng cách mặt-camera qua IPD
        
        IPD tăng = ngồi gần, IPD giảm = ngồi xa
        """
        left_eye = face_landmarks.landmark[FaceMeshLandmarks.LEFT_EYE_OUTER]
        right_eye = face_landmarks.landmark[FaceMeshLandmarks.RIGHT_EYE_OUTER]
        
        return math.sqrt(
            (left_eye.x - right_eye.x) ** 2 +
            (left_eye.y - right_eye.y) ** 2
        )

    def reset(self):
        self.bad_posture_counter = 0
        self.is_bad_posture = False

