import math 
from typing import Tuple, Optional
import mediapipe as mp

# Đầu file - thêm constants cho Face Mesh landmarks
class FaceMeshLandmarks:
    """Landmarks quan trọng từ MediaPipe Face Mesh (478 điểm)"""
    # Mắt trái
    LEFT_EYE_OUTER = 33
    LEFT_EYE_INNER = 133
    
    # Mắt phải  
    RIGHT_EYE_OUTER = 263
    RIGHT_EYE_INNER = 362
    
    # Khuôn mặt để tính Head Pitch
    FOREHEAD = 10        # Trán
    NOSE_TIP = 1         # Đầu mũi
    CHIN = 152           # Cằm
    
    # Hai bên mặt (để tính head yaw nếu cần)
    LEFT_CHEEK = 234
    RIGHT_CHEEK = 454
    def calculate_head_pitch(self, face_landmarks) -> float:
          """tính góc cúi đầu từ face mesh"""
          forehaed = face_landmarks.landmark[FaceMeshLandmarks.FOREHEAD]
          nose = face_landmarks.landmark[FaceMeshLandmarks.NOSE_TIP]
          chin = face_landmarks.landmark[FaceMeshLandmarks.CHIN]
          # tính vector từ forehead đến chin 
          face_vector_y = chin.y - forehaed.y
          face_vector_z = chin.z - forehaed.z
          # tinhs góc p pitch (nghiêng lên xuống)
          pitch = math.degrees(math.atan2(face_vector_z , face_vector_y))
          return pitch
    def calculate_face_distance(self, face_landmarks) -> float:
         """ ước tính tương đối từ mặt đến camera"""
         """ dựa vào khoảng cách giữa 2 mắt """
         left_eye = face_landmarks.landmark[FaceMeshLandmarks.LEFT_EYE_OUTER]
         right_eye = face_landmarks.landmark[FaceMeshLandmarks.RIGHT_EYE_OUTER]
         ipd = math.sqrt(
                 (left_eye.x - right_eye.x) ** 2 +
                     (left_eye.y - right_eye.y) ** 2 
         )
         return ipd


class PostureAnalyzer:
     def __init__(self , head_tilt_threshold: float = 15.0 , posture_frames: int = 30):
          """ khởi tao Posture Analyzer 
          head_tilt_threshold: góc nghiêng đầu tối đa (độ)
          posture_frames : số khung hình liên tiếp để xác định tư thế xấu 
          """
          self.head_tilt_threshold = head_tilt_threshold
          self.posture_frames = posture_frames
          self.bad_posture_counter = 0
          self.is_bad_posture = False
          self.mp_pose = mp.solutions.pose
     @staticmethod
     def calculate_angle(p1 , p2 , p3) -> float:
          v1 = [p2.x - p1.x , p2.y - p1.y]
          v2 = [p3.x - p2.x , p3.y - p2.y]
          
          dot = v1[0]*v2[0] + v1[1]*v2[1]
          mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
          mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
          if mag1 == 0 or mag2 == 0:
               return 0.0
          cos_angle = dot / (mag1 * mag2)
          cos_angle = max(-1.0 , min(1.0 , cos_angle))
          angle = math.acos(cos_angle)
          return math.degrees(angle)
     def calculate_head_tilt(self , landmarks) -> float:
          """tính góc nghiêng của đầu 
          dựa trên góc giữa : 
          - mũi (NOSE)
          - điểm giữa vai """
          nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
          left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
          right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
          mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
          vertical_diff = abs(nose.y - mid_shoulder_y)
          if nose.y > mid_shoulder_y:
               # gù lưng cúi đầu 
               tilt_score = vertical_diff * 100 
          else:
               tilt_score = 0
          return tilt_score
     def calculate_shoulder_angle(self ,landmarks) -> float:
          """ tính góc nghiêng vai """
          left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
          right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
          dx = right_shoulder.x - left_shoulder.x
          dy = right_shoulder.y - left_shoulder.y
          if dx == 0:
               return 0.0
          angle = math.degrees(math.atan(dy / dx))
          return abs(angle)

     def calculate_posture_score(self , head_tilt: float , shoulder_angle: float)-> float:
          """ tính điểm tư thế tổng hợp(0 - 100)
          args :
          head_tilt: góc nghiêng đầu 
          shoulder_angle: góc nghiêng vai 
          """
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
     def process(self , pose_landmarks) -> Tuple[float , float , float , bool]:
          if pose_landmarks is None:
               return 0.0 , 0.0 , 100 , False
          landmarks = pose_landmarks.landmark
          head_tilt = self.calculate_head_tilt(landmarks)
          shoulder_angle = self.calculate_shoulder_angle(landmarks)
          posture_score = self.calculate_posture_score(head_tilt , shoulder_angle)
          if head_tilt > self.head_tilt_threshold or shoulder_angle < 20:
               self.bad_posture_counter += 1
          else:
               self.bad_posture_counter = 0
               self.is_bad_posture = False
          if self.bad_posture_counter >= self.posture_frames:
               self.is_bad_posture = True
          return head_tilt , shoulder_angle , posture_score , self.is_bad_posture
     def reset(self):
          self.bad_posture_counter = 0
          self.is_bad_posture = False


