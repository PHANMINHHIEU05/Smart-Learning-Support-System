import math
from typing import Tuple


class DrowsinessDetector:
    """Phát hiện buồn ngủ dựa trên EAR (Eye Aspect Ratio)"""
    
    # Face Mesh landmarks cho mắt
    LEFT_EYE = {'upper': 386, 'lower': 374, 'left': 263, 'right': 362}
    RIGHT_EYE = {'upper': 159, 'lower': 145, 'left': 133, 'right': 33}
    
    def __init__(self, ear_threshold: float = 0.2, consec_frames: int = 20):
        self.ear_threshold = ear_threshold
        self.consec_frames = consec_frames
        self.eye_closed_counter = 0
        self.is_drowsy = False
        self.micro_sleep_threshold = 90
        self.microsleep_max_frams = 300
        self.microsleep_counter = 0
        self.is_microsleep = False

        self.last_head_pitch = 0.0
        self.head_pitch_history = [] # lưu 30 frame gần nhất 
        self.head_movememt_threshold = 5.0

    @staticmethod
    def calculate_distance(p1, p2) -> float:
        """Khoảng cách Euclidean 3D giữa 2 điểm"""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def calculate_ear(self, landmarks, eye_points: dict) -> float:
        """EAR = vertical_distance / horizontal_distance"""
        upper = landmarks[eye_points['upper']]
        lower = landmarks[eye_points['lower']]
        left = landmarks[eye_points['left']]
        right = landmarks[eye_points['right']]
        
        vertical = self.calculate_distance(upper, lower)
        horizontal = self.calculate_distance(left, right)
        
        if horizontal == 0:
            return 0.0
        return vertical / horizontal

    def process(self, face_landmarks) -> Tuple[float, float, bool]:
        """Xử lý face landmarks và trả về (ear_left, ear_right, is_drowsy)"""
        if face_landmarks is None:
            return 0.0, 0.0, False
        
        landmarks = face_landmarks.landmark
        ear_left = self.calculate_ear(landmarks, self.LEFT_EYE)
        ear_right = self.calculate_ear(landmarks, self.RIGHT_EYE)
        ear_avg = (ear_left + ear_right) / 2.0

        if ear_avg < self.ear_threshold:
            self.eye_closed_counter += 1
        else:
            self.eye_closed_counter = 0
            self.is_drowsy = False
            
        if self.eye_closed_counter >= self.consec_frames:
            self.is_drowsy = True
            
        return ear_left, ear_right, self.is_drowsy

    def reset(self):
        self.eye_closed_counter = 0
        self.is_drowsy = False
