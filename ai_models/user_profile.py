import json 
import os 
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict, field

@dataclass
class CalibrationData:
     """ lữu trữ dữ liệu calibration cho 1 chỉ số :
     Attributes:
          mean: giá trị trung bình
          std: độ lệch chuẩn 
          min_val :  giá trị nhỏ  nhất trong calibration 
          max_val : giá trị lớn nhất trong calibration
          sample_count:  số mẫu đã thu thập 
     """
     mean: float = 0.0
     std : float = 0.0
     min_val: float = 0.0
     max_val: float = 0.0
     sample_count: int =  0
@dataclass
class UserProfile:
     """ profile cá nhân hóa của người dùng được tạo sau 10 giây đầu lưu trữ ngưỡng cá nhân """
     user_id: str = "default_user"
     created_at: str = ""
     is_calibrated: bool = False
     # dữ liệu calobration cho ear
     ear_data: CalibrationData = field(default_factory= CalibrationData)
     # dữ liệu cho tư thế 
     head_tilt_data: CalibrationData = field(default_factory= CalibrationData)
     shoulder_angle_data: CalibrationData = field(default_factory= CalibrationData)
     # dữ liệu dành cho khoảng cách(ước tinh)
     distance_data: CalibrationData = field(default_factory= CalibrationData)
     
     def __post_init__(self):
          """khởi tạo timestamp nếu chưa có """
          if not self.created_at:
               self.created_at = datetime.now().isoformat()
     def calculate_z_score(self , current_value: float, calib_data : CalibrationData) -> float:
          if calib_data.std ==  0:
               return 0.0
          z_score = (current_value - calib_data.mean) / calib_data.std
          return z_score
     def get_ear_z_score(self, current_ear: float) -> float:
          return self.calculate_z_score(current_ear , self.ear_data)
     def get_head_tilt_z_score(self , current_tilt: float) -> float:
          return self.calculate_z_score(current_tilt , self.head_tilt_data)
     def get_shoulder_angle_z_score(self , current_angle: float) -> float:
          return self.calculate_z_score(current_angle , self.shoulder_angle_data)
     def is_drowsy(self, current_ear: float , threshold: float = -2.0) -> bool:
          """kiểm tra buồn ngủ dựa trên z-score của EAR
          điều kiện : Z_EAR < threshold(mặc định -2.0)
          Giải thích:
          - khi buồn ngủ, EAR giảm (mắt nhắm )
          - Z_SCORE âm = EAR thấp hơn bình thường 
          - Z < -2 nghĩa là thấp hơn 2 độ lệch chuẩn 
          """
          z_score = self.get_ear_z_score(current_ear)
          return z_score < threshold
     def is_bad_posture(self, current_head_tilt: float , 
                        current_shoulder_angle: float,
                        threshould: float = 2.0) -> bool:
          z_head = abs(self.get_head_tilt_z_score(current_head_tilt))
          z_shoulder = abs(self.get_shoulder_angle_z_score(current_shoulder_angle))
          return z_head > threshould or z_shoulder > threshould
     def save_to_file(self, filepath: str = "data/user_profile.json")-> bool:
          """ Lưu profile ra file json """
          try:
               os.makedirs(os.path.dirname(filepath), exist_ok=True)
               data = {
                    'user_id': self.user_id,
                    'created_at': self.created_at,
                    'is_calibrated': self.is_calibrated,
                    'ear_data': asdict(self.ear_data),
                    'head_tilt_data': asdict(self.head_tilt_data),
                    'shoulder_angle_data': asdict(self.shoulder_angle_data),
                    'distance_data': asdict(self.distance_data)
               }
               with open(filepath, 'w') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
               print(f"✅ User profile đã được lưu tại {filepath}")
               return True
          except Exception as e:
               print(f"❌ Lỗi lưu user profile: {e}")
               return False
     @classmethod
     def load_from_file(cls, filepath: str = "data/user_profile.json") -> Optional['UserProfile']:
          """ Tải profile từ file json """
          try: 
               if not os.path.exists(filepath):
                    print(f"⚠️ File user profile không tồn tại: {filepath}")
                    return None
               with open (filepath , 'r') as f:
                    data = json.load(f)
               profile = cls(
                    user_id = data.get('user_id', 'default_user'),
                    created_at = data.get('created_at', ''),
                    is_calibrated = data.get('is_calibrated', False),
                    ear_data = CalibrationData(**data.get('ear_data', {})),
                    head_tilt_data = CalibrationData(**data.get('head_tilt_data', {})),
                    shoulder_angle_data = CalibrationData(**data.get('shoulder_angle_data', {})),
                    distance_data = CalibrationData(**data.get('distance_data', {}))
               )
               print(f"✅ User profile đã được tải từ {filepath}")
               return profile
          except Exception as e:
               print(f"❌ Lỗi tải user profile: {e}")
               return None
     def __str__(self) -> str:
          return f"UserProfile(user_id={self.user_id}, is_calibrated={self.is_calibrated})"