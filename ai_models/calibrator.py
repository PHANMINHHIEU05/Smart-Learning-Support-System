import time 
import math 
from typing import List, Optional
from ai_models.user_profile import UserProfile, CalibrationData


class Calibrator:
    """Bộ hiệu chuẩn - thu thập dữ liệu baseline trong 10 giây"""
    
    def __init__(self, duration: float = 10.0):
        self.duration = duration
        
        # Buffers cho các mẫu dữ liệu
        self.ear_samples: List[float] = []
        self.head_tilt_samples: List[float] = []
        self.shoulder_angle_samples: List[float] = []
        self.distance_samples: List[float] = []
        self.head_pitch_samples: List[float] = []
        self.ipd_samples: List[float] = []
        
        self.is_calibrating: bool = False
        self.start_time: Optional[float] = None
        self.progress: float = 0.0

    def reset(self):
        self.ear_samples.clear()
        self.head_tilt_samples.clear()
        self.shoulder_angle_samples.clear()
        self.distance_samples.clear()
        self.head_pitch_samples.clear()
        self.ipd_samples.clear()
        self.is_calibrating = False
        self.start_time = None
        self.progress = 0.0

    def start(self):
        self.reset()
        self.is_calibrating = True
        self.start_time = time.time()
        print("🔄 Bắt đầu hiệu chuẩn - Vui lòng giữ tư thế bình thường...")

    def add_sample(self, ear_avg: float, head_tilt: float, shoulder_angle: float, 
                   distance: float, head_pitch: float = 0.0, ipd: float = 0.0):
        """Thêm mẫu dữ liệu vào buffer"""
        if not self.is_calibrating:
            return
        
        self.ear_samples.append(ear_avg)
        self.head_tilt_samples.append(head_tilt)
        self.shoulder_angle_samples.append(shoulder_angle)
        self.distance_samples.append(distance)
        self.head_pitch_samples.append(head_pitch)
        self.ipd_samples.append(ipd)
        
        elapsed = time.time() - self.start_time
        self.progress = min(elapsed / self.duration, 1.0)

    def is_complete(self) -> bool:
        if not self.is_calibrating or self.start_time is None:
            return False
        return time.time() - self.start_time >= self.duration

    @staticmethod
    def calculate_statistics(samples: List[float]) -> CalibrationData:
        """Tính mean, std, min, max từ danh sách mẫu"""
        if len(samples) == 0:
            return CalibrationData()
        
        n = len(samples)
        mean = sum(samples) / n
        variance = sum((x - mean) ** 2 for x in samples) / n
        std = math.sqrt(variance)
        
        return CalibrationData(
            mean=mean,
            std=std,
            min_val=min(samples),
            max_val=max(samples),
            sample_count=n
        )

    def finish(self) -> Optional[UserProfile]:
        """Hoàn thành calibration và tạo UserProfile"""
        if len(self.ear_samples) < 30:
            print("❌ Không đủ mẫu dữ liệu (cần ít nhất 30)")
            return None
        
        profile = UserProfile(
            is_calibrated=True,
            ear_data=self.calculate_statistics(self.ear_samples),
            head_tilt_data=self.calculate_statistics(self.head_tilt_samples),
            shoulder_angle_data=self.calculate_statistics(self.shoulder_angle_samples),
            distance_data=self.calculate_statistics(self.distance_samples),
            head_pitch_data=self.calculate_statistics(self.head_pitch_samples),
            ipd_data=self.calculate_statistics(self.ipd_samples)
        )
        
        self.is_calibrating = False
        print("✅ Hiệu chuẩn hoàn tất!")
        print(f"   📊 EAR: Mean={profile.ear_data.mean:.4f}, Std={profile.ear_data.std:.4f}")
        print(f"   📊 Head Pitch: Mean={profile.head_pitch_data.mean:.2f}°")
        print(f"   📊 IPD: Mean={profile.ipd_data.mean:.4f}")
        
        return profile

    def get_progress_bar(self, length: int = 30) -> str:
        filled = int(length * self.progress)
        bar = '█' * filled + '-' * (length - filled)
        return f"|{bar}| {int(self.progress * 100)}%"

