"""phát hiện bất thường dựa trên z_score mà mình đã lấy từ trước s"""
"""so sánh giá trị hiện tại với profile mà mình đã thu thập từ 10s"""
from typing import Optional, Tuple , Dict
from dataclasses import dataclass
from ai_models.user_profile import UserProfile, CalibrationData
from ai_models.moving_average_filter import MovingAverageFilter, MultiChannelFilter

@dataclass
class DetectionResult:
     raw_ear: float = 0.0
     raw_head_tilt: float = 0.0
     raw_shoulder_angle: float = 0.0
     #giá trị làm mượt 
     smoothed_ear: float = 0.0
     smoothed_head_tilt: float = 0.0
     smoothed_shoulder_angle: float = 0.0

     # z-scores
     z_ear: float = 0.0
     z_head_tilt: float = 0.0
     z_shoulder: float = 0.0

     # detect flags
     is_drowsy: bool = False
     is_bad_posture: bool = False
     # counters(số frame liên tiếp bất thường)
     drowsy_frames: int = 0
     bad_posture_frames: int = 0
class AdaptiveDetector:
     """bộ phát hiện bất thường 
     1. lấy từ userprfiule , tính z-score 
     phát hiện bất thường từ z-score 
     """
     def __init__(self, user_profile: UserProfile,
                  z_threshold_drowsy: float = -2.0,
                  z_threshold_posture: float = 2.0,
                  consecutive_frames: int = 15,
                  filter_window: int = 7):
          self.profile = user_profile
          self.z_threshold_drowsy = z_threshold_drowsy
          self.z_threshold_posture = z_threshold_posture
          self.consecutive_frames = consecutive_frames
          # tạo bộ lọc dành cho các kênh 
          self.filters = MultiChannelFilter(
               channels=['ear', 'head_tilt', 'shoulder_angle'],
               window_size=filter_window,
               method='ema'
          )
          self.drowsy_counter = 0
          self.bad_posture_counter = 0
          # lưu kết quả cuối cùng 
          self.last_result: Optional[DetectionResult] = None
     def calculate_z_score(self, value: float, calib_data: CalibrationData) -> float:
          """tính z_score cho 1 giá trị
          Công thức: Z = (x - μ) / σ
        
        Ý nghĩa:
        - Z = 0: Giá trị bằng trung bình
        - Z = -1: Thấp hơn 1 độ lệch chuẩn
        - Z = -2: Thấp hơn 2 độ lệch chuẩn (bất thường)
        - Z = +2: Cao hơn 2 độ lệch chuẩn (bất thường)
        
        Theo phân phối chuẩn:
        - 68.2% dữ liệu nằm trong ±1σ
        - 95.4% dữ liệu nằm trong ±2σ
        - 99.7% dữ liệu nằm trong ±3σ
        
        → |Z| > 2 nghĩa là chỉ có 4.6% khả năng là bình thường 
          """
          if calib_data.std == 0 or calib_data.std is None:
               return 0.0
          z = (value - calib_data.mean) / calib_data.std
          return z
     def process(self, ear_avg: float, head_tilt: float, shoulder_angle: float)-> DetectionResult:
          """xử lý 1 frame và phát hiện bất thường """
          """cho vào 3 giá trị thô và trả vể kết quả phân tích đầy đủ""" 
          result = DetectionResult()
          smoothed = self.filters.update({
               'ear': ear_avg,
               'head_tilt': head_tilt,
               'shoulder_angle': shoulder_angle
          })
          result.smoothed_ear = smoothed['ear']
          result.smoothed_head_tilt = smoothed['head_tilt']
          result.smoothed_shoulder_angle = smoothed['shoulder_angle']

          result.z_ear = self.calculate_z_score(
               result.smoothed_ear,
               self.profile.ear_data
          )
          result.z_head_tilt = self.calculate_z_score(
               result.smoothed_head_tilt,
               self.profile.head_tilt_data
          )
          result.z_shoulder = self.calculate_z_score(
               result.smoothed_shoulder_angle,
               self.profile.shoulder_angle_data
          )
          if result.z_ear < self.z_threshold_drowsy:
               self.drowsy_counter += 1
          else:
               self.drowsy_counter = 0
          result.drowsy_frames = self.drowsy_counter
          result.is_drowsy = self.drowsy_counter >= self.consecutive_frames
          if (abs(result.z_head_tilt) > self.z_threshold_posture or abs(result.z_shoulder) > self.z_threshold_posture):
               self.bad_posture_counter += 1
          else:
               self.bad_posture_counter = 0
          result.bad_posture_frames = self.bad_posture_counter
          result.is_bad_posture = self.bad_posture_counter >= self.consecutive_frames
          self.last_result = result
          return result
     def reset(self):
          """đặt lại bộ phát hiện """
          self.filters.reset()
          self.drowsy_counter = 0
          self.bad_posture_counter = 0
          self.last_result = None
     def get_status_text(self) -> str:
          """
          Lấy text mô tả trạng thái hiện tại
          
          Returns:
               str: Mô tả trạng thái
          """
          if self.last_result is None:
               return "Chưa có dữ liệu"
          
          r = self.last_result
          
          status_parts = []
          
          # EAR status
          if r.is_drowsy:
               status_parts.append(f"BUỒN NGỦ (Z={r.z_ear:.2f})")
          elif r.z_ear < -1:
               status_parts.append(f"Hơi mệt (Z={r.z_ear:.2f})")
          else:
               status_parts.append(f"Tỉnh táo (Z={r.z_ear:.2f})")
          
          # Posture status
          if r.is_bad_posture:
               status_parts.append(f"TƯ THẾ XẤU")
          else:
               status_parts.append(f"Tư thế tốt")
          
          return " | ".join(status_parts)