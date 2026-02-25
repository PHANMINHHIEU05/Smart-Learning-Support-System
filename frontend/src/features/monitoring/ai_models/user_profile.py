import json 
import os 
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict, field


@dataclass
class CalibrationData:
    """Dữ liệu calibration cho 1 chỉ số (mean, std, min, max)"""
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    sample_count: int = 0


@dataclass
class UserProfile:
    """Profile cá nhân hóa được tạo sau 10 giây calibration"""
    user_id: str = "default_user"
    created_at: str = ""
    is_calibrated: bool = False
    
    # Calibration data
    ear_data: CalibrationData = field(default_factory=CalibrationData)
    head_tilt_data: CalibrationData = field(default_factory=CalibrationData)
    shoulder_angle_data: CalibrationData = field(default_factory=CalibrationData)
    distance_data: CalibrationData = field(default_factory=CalibrationData)
    head_pitch_data: CalibrationData = field(default_factory=CalibrationData)
    ipd_data: CalibrationData = field(default_factory=CalibrationData)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def calculate_z_score(self, current_value: float, calib_data: CalibrationData) -> float:
        """Tính Z-score: Z = (x - μ) / σ"""
        if calib_data.std == 0:
            return 0.0
        return (current_value - calib_data.mean) / calib_data.std

    def get_ear_z_score(self, current_ear: float) -> float:
        return self.calculate_z_score(current_ear, self.ear_data)

    def get_head_tilt_z_score(self, current_tilt: float) -> float:
        return self.calculate_z_score(current_tilt, self.head_tilt_data)

    def get_shoulder_angle_z_score(self, current_angle: float) -> float:
        return self.calculate_z_score(current_angle, self.shoulder_angle_data)

    def get_head_pitch_z_score(self, current_pitch: float) -> float:
        """Z > 2: Cúi đầu quá nhiều, Z < -2: Ngẩng đầu quá nhiều"""
        return self.calculate_z_score(current_pitch, self.head_pitch_data)

    def get_ipd_z_score(self, current_ipd: float) -> float:
        """Z > 2: Ngồi quá gần, Z < -2: Ngồi quá xa"""
        return self.calculate_z_score(current_ipd, self.ipd_data)

    def is_too_close(self, current_ipd: float, threshold: float = 2.0) -> bool:
        return self.get_ipd_z_score(current_ipd) > threshold

    def is_head_down(self, current_pitch: float, threshold: float = 2.0) -> bool:
        return self.get_head_pitch_z_score(current_pitch) > threshold

    def is_drowsy(self, current_ear: float, threshold: float = -2.0) -> bool:
        """Z < -2: Mắt nhắm, buồn ngủ"""
        return self.get_ear_z_score(current_ear) < threshold

    def is_bad_posture(self, current_head_tilt: float, current_shoulder_angle: float,
                       threshold: float = 2.0) -> bool:
        z_head = abs(self.get_head_tilt_z_score(current_head_tilt))
        z_shoulder = abs(self.get_shoulder_angle_z_score(current_shoulder_angle))
        return z_head > threshold or z_shoulder > threshold

    def save_to_file(self, filepath: str = "data/user_profile.json") -> bool:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            data = {
                'user_id': self.user_id,
                'created_at': self.created_at,
                'is_calibrated': self.is_calibrated,
                'ear_data': asdict(self.ear_data),
                'head_tilt_data': asdict(self.head_tilt_data),
                'shoulder_angle_data': asdict(self.shoulder_angle_data),
                'distance_data': asdict(self.distance_data),
                'head_pitch_data': asdict(self.head_pitch_data),
                'ipd_data': asdict(self.ipd_data)
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
        try:
            if not os.path.exists(filepath):
                print(f"⚠️ File không tồn tại: {filepath}")
                return None
            with open(filepath, 'r') as f:
                data = json.load(f)
            profile = cls(
                user_id=data.get('user_id', 'default_user'),
                created_at=data.get('created_at', ''),
                is_calibrated=data.get('is_calibrated', False),
                ear_data=CalibrationData(**data.get('ear_data', {})),
                head_tilt_data=CalibrationData(**data.get('head_tilt_data', {})),
                shoulder_angle_data=CalibrationData(**data.get('shoulder_angle_data', {})),
                distance_data=CalibrationData(**data.get('distance_data', {})),
                head_pitch_data=CalibrationData(**data.get('head_pitch_data', {})),
                ipd_data=CalibrationData(**data.get('ipd_data', {}))
            )
            print(f"✅ User profile đã được tải từ {filepath}")
            return profile
        except Exception as e:
            print(f"❌ Lỗi tải user profile: {e}")
            return None

    def __str__(self) -> str:
        return f"UserProfile(user_id={self.user_id}, is_calibrated={self.is_calibrated})"
