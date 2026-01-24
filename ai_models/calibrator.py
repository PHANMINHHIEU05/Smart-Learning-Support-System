import time 
import math 
from typing import List , Optional , Dict , Callable
from ai_models.user_profile import UserProfile , CalibrationData

class Calibrator:
     def __init__(self, duration: float = 10.0 ):
          """ khởi tạo bộ hiệu chuẩn 
          duration: thời gian hiệu chuẩn (giây)
          """
          # thời gian hiệu chuẩn
          self.duration = duration
          # bộ đệm mẫu dữ liệu
          self.ear_samples: List[float] = []
          self.head_tilt_samples: List[float] = []
          self.shoulder_angle_samples: List[float] = []
          self.distance_samples: List[float] = []

          #trạng thái
          self.is_calibrating: bool = False
          self.start_time: Optional[float] = None
          self.progress: float = 0.0 
     def reset(self):
          """đặt lại bộ hiệu chuẩn """
          self.ear_samples.clear()
          self.head_tilt_samples.clear()
          self.shoulder_angle_samples.clear()
          self.distance_samples.clear()
          self.is_calibrating = False
          self.start_time = None
          self.progress = 0.0
     def start(self):
          """bắt đầu hiệu chuẩn """
          self.reset()
          self.is_calibrating = True
          self.start_time = time.time()
          print("Bắt đầu hiệu chuẩn người dùng...")
          print("Vui lòng giữ tư thế bình thường trong quá trình hiệu chuẩn.")
     def add_sample(self, ear_avg: float , head_tilt: float, shoulder_angle: float, distance: float):
          """thêm một mẫu dữ liệu chuẩn vào buffer
          args:
          ear_avg: giá trị ear trung bình
          head_tilt: góc nghiêng đầu
          shoulder_angle: góc nghiêng vai
          distance: khoảng cách ước tính đến camera
          """
          if not self.is_calibrating:
               return
          self.ear_samples.append(ear_avg)
          self.head_tilt_samples.append(head_tilt)
          self.shoulder_angle_samples.append(shoulder_angle)
          self.distance_samples.append(distance)
          elapsed = time.time() - self.start_time
          self.progress = min(elapsed / self.duration , 1.0)
     def is_complete(self) -> bool:
          if not  self.is_calibrating or self.start_time is None:
               return False
          elapsed = time.time() - self.start_time
          return elapsed >= self.duration
     @staticmethod
     def calculate_statistics(samples: List[float]) -> CalibrationData:
          """tính toán các thống kê cơ bản từ mẫu dữ liệu
          args:
          samples: danh sách mẫu dữ liệu
          
          returns:
          CalibrationData chứa mean, std, min, max, sample_count
          """
          if len(samples) == 0:
               return CalibrationData()
          n = len(samples)
          mean = sum(samples) / n
          variance = sum((x - mean) ** 2 for x in samples) / n
          std = math.sqrt(variance)
          min_val = min(samples)
          max_val = max(samples)
          return CalibrationData(
               mean=mean,
               std=std,
               min_val=min_val,
               max_val=max_val,
               sample_count=n
          )
     def finish(self) -> UserProfile:
          if len(self.ear_samples) < 30:
               print("❌ Không đủ mẫu dữ liệu để hoàn thành hiệu chuẩn.") # ít nhất 30 mẫu 
               return None 
          ear_data = self.calculate_statistics(self.ear_samples)
          head_tilt_data = self.calculate_statistics(self.head_tilt_samples)
          shoulder_angle_data = self.calculate_statistics(self.shoulder_angle_samples)
          distance_data = self.calculate_statistics(self.distance_samples)
          profile = UserProfile(
               is_calibrated= True,
               ear_data= ear_data,
               head_tilt_data= head_tilt_data,
               shoulder_angle_data= shoulder_angle_data,
               distance_data= distance_data
          )
          self.is_calibrating = False
          print("✅ Hiệu chuẩn hoàn tất.")
          return profile
     def get_progress_bar(self, length: int = 30) -> str:
          """trả về thanh tiến trình dạng text"""
          filled_length = int(length * self.progress)
          bar = '█' * filled_length + '-' * (length - filled_length)
          percent = int(self.progress * 100)
          return f"|{bar}| {percent}%"
          
          