import math
from typing import Tuple, Optional
class DrowsinessDetector:
     """
     phát hiện buồn ngủ dựa trên EAR và thời gian nhắm mắt 
     """
     LEFT_EYE = {
          'upper': 386,
          'lower': 374,
          'left': 263,
          'right': 362
     }
     RIGHT_EYE = {
          'upper': 159,
          'lower': 145,
          'left': 133,
          'right': 33
     }
     def __init__(self , ear_threshold: float = 0.2 , consec_frames: int = 20):
          """khởi tạo Drowsisness Detector"""
          self.ear_threshold = ear_threshold
          self.consec_frames = consec_frames

          self.eye_closed_counter = 0
          self.is_drowsy = False
     @staticmethod
     def caculate_distane(p1 , p2) -> float:
          """tính khoảng cách Euclidean giữa 2 điểm"""
          return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)
     def calculate_ear(self , landmarks , eye_points: dict) -> float:
          """tính Eye  aspect ratio cho 1 mắt"""
          upper = landmarks[eye_points['upper']]
          lower = landmarks[eye_points['lower']]
          left = landmarks[eye_points['left']]
          right = landmarks[eye_points['right']]
          vertical_distance = self.caculate_distane(upper , lower)
          horizontal_distance = self.caculate_distane(left , right)
          if horizontal_distance == 0:
               return 0.0
          ear = vertical_distance / horizontal_distance
          return ear
     
     def process(self , face_landmarks) -> Tuple[float , float , bool ] :
          """ xử lý face landmarks và phát hiện buồn ngủ """
          if face_landmarks is None:
               return 0.0 , 0.0 , False
          landmarks = face_landmarks.landmark

          # tính EAR cho 2 mắt 
          ear_left = self.calculate_ear(landmarks , self.LEFT_EYE)
          ear_right = self.calculate_ear(landmarks , self.RIGHT_EYE)
          ear_avg = (ear_left + ear_right) / 2.0

          if ear_avg < self.ear_threshold:
               self.eye_closed_counter += 1
          else :
               self.eye_closed_counter = 0 
               self.is_drowsy = False
          if self.eye_closed_counter >= self.consec_frames:
               self.is_drowsy = True
          return ear_left , ear_right , self.is_drowsy
     def reset(self):
          self.eye_closed_counter = 0
          self.is_drowsy = False
