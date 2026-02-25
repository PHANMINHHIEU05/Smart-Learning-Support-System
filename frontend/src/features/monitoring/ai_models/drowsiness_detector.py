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
        self.micro_threshold_frame = 90
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
   
    def detect_microsleep(self, ear_avg: float,
                          head_pitch: float,
                          head_yaw: float,
                          head_roll: float) -> Tuple[bool, int]:
        """phát hiện microslepp qua: 
            ear thấp kéo dài 
            đầu cúi dần
            không chuyyeenr động đầu
        """     
        eyes_closed = ear_avg < 0.18
        self.head_pitch_history.append(head_pitch)
        if len(self.head_pitch_history) > 30:
            self.head_pitch_history.pop(0)
        head_movement = 0
        if len(self.head_pitch_history) >= 10:
            head_movement = max(self.head_pitch_history) - min(self.head_pitch_history)
        is_head_stable = head_movement < self.head_movememt_threshold
        is_head_drooping = head_pitch > 15
        if eyes_closed and is_head_stable and is_head_drooping:
            self.microsleep_counter += 1
        else:
            self.microsleep_counter = 0
            self.is_microsleep = False
            return False, 0
        if self.microsleep_counter >= self.micro_threshold_frame:
            self.is_microsleep = True
            return True, self.microsleep_counter
        return False, 0
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
