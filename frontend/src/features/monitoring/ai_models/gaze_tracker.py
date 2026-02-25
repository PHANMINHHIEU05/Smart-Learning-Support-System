from typing import Tuple, Optional


# MediaPipe Face Mesh Landmarks
LEFT_EYE_OUTER = 33      # Góc ngoài mắt trái
LEFT_EYE_INNER = 133     # Góc trong mắt trái
RIGHT_EYE_OUTER = 263    # Góc ngoài mắt phải
RIGHT_EYE_INNER = 362    # Góc trong mắt phải
LEFT_IRIS_CENTER = 468   # Tâm iris trái
RIGHT_IRIS_CENTER = 473  # Tâm iris phải


class GazeTracker:
    """Theo dõi hướng nhìn dựa trên vị trí iris trong mắt
    Gaze ratio:
    - 0.0 ~ 0.35: Nhìn TRÁI
    - 0.35 ~ 0.65: Nhìn GIỮA (CENTER) - tập trung
    - 0.65 ~ 1.0: Nhìn PHẢI
    """
    
    def __init__(self, left_threshold: float = 0.35, 
                 right_threshold: float = 0.65, 
                 distraction_frames: int = 30):
        self.left_threshold = left_threshold
        self.right_threshold = right_threshold
        self.distraction_frames = distraction_frames
        
        # Trạng thái
        self.distraction_counter = 0
        self.is_distracted = False
        self.current_direction = "CENTER"
        self.current_ratio = 0.5

    def _calculate_distance(self, p1, p2) -> float:
        return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5

    def _get_iris_position(self, landmarks) -> float:
        """Tính vị trí tương đối của iris trong mắt (0-1)
        
        Returns:
            float: Gaze ratio (0.5 = nhìn thẳng)
        """
        left_iris_x = landmarks[LEFT_IRIS_CENTER].x
        left_eye_outer_x = landmarks[LEFT_EYE_OUTER].x
        left_eye_inner_x = landmarks[LEFT_EYE_INNER].x
        
        left_eye_width = left_eye_inner_x - left_eye_outer_x
        if abs(left_eye_width) < 0.001:  
            left_ratio = 0.5
        else:
            left_iris_offset = left_iris_x - left_eye_outer_x
            left_ratio = left_iris_offset / left_eye_width
        right_iris_x = landmarks[RIGHT_IRIS_CENTER].x
        right_eye_outer_x = landmarks[RIGHT_EYE_OUTER].x
        right_eye_inner_x = landmarks[RIGHT_EYE_INNER].x
        
        right_eye_width = right_eye_outer_x - right_eye_inner_x  
        if abs(right_eye_width) < 0.001:
            right_ratio = 0.5
        else:
            right_iris_offset = right_eye_outer_x - right_iris_x  # Ngược chiều
            right_ratio = right_iris_offset / right_eye_width
        avg_ratio = (left_ratio + right_ratio) / 2.0
        return max(0.0, min(1.0, avg_ratio))

    def _determine_direction(self) -> str:
        if self.current_ratio < self.left_threshold:
            return "LEFT"
        elif self.current_ratio > self.right_threshold:
            return "RIGHT"
        else:
            return "CENTER"

    def process(self, face_landmarks) -> Tuple[float, str, bool]:
        if face_landmarks is None:
            return 0.5, "CENTER", False
        
        landmarks = face_landmarks.landmark
        
        self.current_ratio = self._get_iris_position(landmarks)
        direction = self._determine_direction()
        if direction != "CENTER":
            self.distraction_counter += 1
        else:
            self.distraction_counter = 0
            self.is_distracted = False        
        if self.distraction_counter >= self.distraction_frames:
            self.is_distracted = True
        self.current_direction = direction
        return self.current_ratio, direction, self.is_distracted

    def reset(self):
        self.distraction_counter = 0
        self.is_distracted = False
        self.current_direction = "CENTER"
        self.current_ratio = 0.5