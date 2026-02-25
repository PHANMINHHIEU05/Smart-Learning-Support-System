from typing import Optional
from dataclasses import dataclass
from ai_models.user_profile import UserProfile, CalibrationData
from ai_models.moving_average_filter import MultiChannelFilter


@dataclass
class DetectionResult:
    """Kết quả phân tích từ Adaptive Detector"""
    # Giá trị thô
    raw_ear: float = 0.0
    raw_head_tilt: float = 0.0
    raw_shoulder_angle: float = 0.0
    raw_head_pitch: float = 0.0
    raw_ipd: float = 0.0
    
    # Giá trị đã làm mượt
    smoothed_ear: float = 0.0
    smoothed_head_tilt: float = 0.0
    smoothed_shoulder_angle: float = 0.0
    smoothed_head_pitch: float = 0.0
    smoothed_ipd: float = 0.0

    # Z-scores
    z_ear: float = 0.0
    z_head_tilt: float = 0.0
    z_shoulder: float = 0.0
    z_head_pitch: float = 0.0
    z_ipd: float = 0.0

    # Detection flags
    is_drowsy: bool = False
    is_bad_posture: bool = False
    is_head_down: bool = False
    is_too_close: bool = False
    
    # Counters
    drowsy_frames: int = 0
    bad_posture_frames: int = 0
    head_down_frames: int = 0
    too_close_frames: int = 0


class AdaptiveDetector:
    """Phát hiện bất thường dựa trên Z-score so với profile đã calibrate"""
    
    def __init__(self, user_profile: UserProfile,
                 z_threshold_drowsy: float = -2.0,
                 z_threshold_posture: float = 2.0,
                 z_threshold_distance: float = 2.0,
                 consecutive_frames: int = 15,
                 filter_window: int = 7):
        
        self.profile = user_profile
        self.z_threshold_drowsy = z_threshold_drowsy
        self.z_threshold_posture = z_threshold_posture
        self.z_threshold_distance = z_threshold_distance
        self.consecutive_frames = consecutive_frames
        
        self.filters = MultiChannelFilter(
            channels=['ear', 'head_tilt', 'shoulder_angle', 'head_pitch', 'ipd'],
            window_size=filter_window,
            method='ema'
        )
        
        self.drowsy_counter = 0
        self.bad_posture_counter = 0
        self.head_down_counter = 0
        self.too_close_counter = 0
        self.last_result: Optional[DetectionResult] = None

    def calculate_z_score(self, value: float, calib_data: CalibrationData) -> float:
        """Z = (x - μ) / σ. |Z| > 2 = bất thường (chỉ 4.6% trong phân phối chuẩn)"""
        if calib_data.std == 0 or calib_data.std is None:
            return 0.0
        return (value - calib_data.mean) / calib_data.std

    def process(self, ear_avg: float, head_tilt: float, shoulder_angle: float,
                head_pitch: float = 0.0, ipd: float = 0.0) -> DetectionResult:
        """Xử lý 1 frame và phát hiện bất thường"""
        result = DetectionResult()
        
        # Lưu giá trị thô
        result.raw_ear = ear_avg
        result.raw_head_tilt = head_tilt
        result.raw_shoulder_angle = shoulder_angle
        result.raw_head_pitch = head_pitch
        result.raw_ipd = ipd
        
        # Làm mượt
        smoothed = self.filters.update({
            'ear': ear_avg, 'head_tilt': head_tilt, 'shoulder_angle': shoulder_angle,
            'head_pitch': head_pitch, 'ipd': ipd
        })
        
        result.smoothed_ear = smoothed['ear']
        result.smoothed_head_tilt = smoothed['head_tilt']
        result.smoothed_shoulder_angle = smoothed['shoulder_angle']
        result.smoothed_head_pitch = smoothed['head_pitch']
        result.smoothed_ipd = smoothed['ipd']

        # Tính Z-scores
        result.z_ear = self.calculate_z_score(result.smoothed_ear, self.profile.ear_data)
        result.z_head_tilt = self.calculate_z_score(result.smoothed_head_tilt, self.profile.head_tilt_data)
        result.z_shoulder = self.calculate_z_score(result.smoothed_shoulder_angle, self.profile.shoulder_angle_data)
        result.z_head_pitch = self.calculate_z_score(result.smoothed_head_pitch, self.profile.head_pitch_data)
        result.z_ipd = self.calculate_z_score(result.smoothed_ipd, self.profile.ipd_data)
        
        # Phát hiện buồn ngủ (Z_EAR < -2)
        if result.z_ear < self.z_threshold_drowsy:
            self.drowsy_counter += 1
        else:
            self.drowsy_counter = 0
        result.drowsy_frames = self.drowsy_counter
        result.is_drowsy = self.drowsy_counter >= self.consecutive_frames
        
        # Phát hiện tư thế xấu
        if (abs(result.z_head_tilt) > self.z_threshold_posture or 
            abs(result.z_shoulder) > self.z_threshold_posture):
            self.bad_posture_counter += 1
        else:
            self.bad_posture_counter = 0
        result.bad_posture_frames = self.bad_posture_counter
        result.is_bad_posture = self.bad_posture_counter >= self.consecutive_frames
        
        # Phát hiện cúi đầu quá mức
        if result.z_head_pitch > self.z_threshold_posture:
            self.head_down_counter += 1
        else:
            self.head_down_counter = 0
        result.head_down_frames = self.head_down_counter
        result.is_head_down = self.head_down_counter >= self.consecutive_frames
        
        # Phát hiện ngồi quá gần
        if result.z_ipd > self.z_threshold_distance:
            self.too_close_counter += 1
        else:
            self.too_close_counter = 0
        result.too_close_frames = self.too_close_counter
        result.is_too_close = self.too_close_counter >= self.consecutive_frames
        
        self.last_result = result
        return result

    def reset(self):
        self.filters.reset()
        self.drowsy_counter = 0
        self.bad_posture_counter = 0
        self.head_down_counter = 0
        self.too_close_counter = 0
        self.last_result = None

    def get_status_text(self) -> str:
        if self.last_result is None:
            return "Chưa có dữ liệu"
        
        r = self.last_result
        status = []
        
        if r.is_drowsy:
            status.append(f"⚠️ BUỒN NGỦ (Z={r.z_ear:.2f})")
        elif r.z_ear < -1:
            status.append(f"😐 Hơi mệt")
        else:
            status.append("✅ Tỉnh táo")
        
        if r.is_bad_posture:
            status.append("⚠️ TƯ THẾ XẤU")
        else:
            status.append("✅ Tư thế tốt")
        
        if r.is_head_down:
            status.append(f"⚠️ CÚI ĐẦU")
        
        if r.is_too_close:
            status.append(f"⚠️ QUÁ GẦN MÀN HÌNH")
        
        return " | ".join(status)
