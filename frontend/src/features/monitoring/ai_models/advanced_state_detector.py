"""
Advanced State Detector - Phát hiện trạng thái học tập phức tạp
Sử dụng NHIỀU METRICS để phát hiện:
- Boredom (buồn chán)
- Dazed (mơ màng/sững sờ)
- Severe Distraction (mất tập trung nghiêm trọng)
"""
import time
from typing import Dict


class AdvancedStateDetector:
    """Kết hợp nhiều metrics để phát hiện trạng thái học tập phức tạp"""
    
    # Thresholds
    BOREDOM_THRESHOLD_FRAMES = 90       # 3 giây liên tục
    DAZED_THRESHOLD_FRAMES = 60         # 2 giây
    SEVERE_DISTRACTION_FRAMES = 120     # 4 giây
    
    def __init__(self):
        # Counters
        self.boredom_counter = 0
        self.dazed_counter = 0
        self.severe_distraction_counter = 0
        
        # States
        self.is_bored = False
        self.is_dazed = False
        self.is_severely_distracted = False
        
        # Tracking
        self.last_blink_time = time.time()
        self.blink_count = 0
        self.low_blink_duration = 0
        
        # History để smooth detection
        self.emotion_history = []
        self.gaze_history = []
        
    def detect_boredom(self, 
                      emotion: str,
                      emotion_conf: float,
                      head_pitch: float,
                      head_yaw: float,
                      gaze_direction: str,
                      blink_rate: float) -> bool:
        """Phát hiện BUỒN CHÁN
        
        Dấu hiệu:
        - Cảm xúc: sad, fear, neutral với confidence cao
        - Đầu nghiêng/quay (không nhìn thẳng)
        - Nhìn xuống hoặc đảo mắt
        - Blink rate thấp (không chớp mắt nhiều)
        
        Args:
            emotion: Cảm xúc hiện tại
            emotion_conf: Độ tin cậy cảm xúc
            head_pitch: Góc cúi/ngẩng đầu
            head_yaw: Góc quay trái/phải
            gaze_direction: Hướng nhìn
            blink_rate: Tần suất chớp mắt (blinks/minute)
        
        Returns:
            bool: True nếu đang buồn chán
        """
        # 1. Cảm xúc buồn/sợ/trung tính
        is_bored_emotion = (
            emotion in ['sad', 'fear', 'neutral'] and 
            emotion_conf > 60
        )
        
        # 2. Đầu cúi xuống hoặc quay sang hẳn
        is_head_down_or_turned = (
            head_pitch > 15 or  # Cúi đầu
            abs(head_yaw) > 25  # Quay đầu sang hẳn
        )
        
        # 3. Không nhìn thẳng
        is_not_looking_center = gaze_direction != "CENTER"
        
        # 4. Blink rate thấp (< 10 blinks/phút = mơ màng)
        is_low_blink = blink_rate < 10
        
        # KẾT HỢP: ít nhất 3/4 điều kiện
        boredom_indicators = sum([
            is_bored_emotion,
            is_head_down_or_turned,
            is_not_looking_center,
            is_low_blink
        ])
        
        if boredom_indicators >= 3:
            self.boredom_counter += 1
        else:
            self.boredom_counter = max(0, self.boredom_counter - 2)
            
        if self.boredom_counter >= self.BOREDOM_THRESHOLD_FRAMES:
            self.is_bored = True
            return True
        else:
            self.is_bored = False
            return False
    
    def detect_dazed(self,
                    ear_avg: float,
                    blink_count_last_10s: int,
                    head_pitch: float,
                    head_roll: float,
                    gaze_direction: str,
                    emotion: str) -> bool:
        """Phát hiện MƠ MÀNG/SỮNG SỜ
        
        Dấu hiệu:
        - EAR thấp nhưng KHÔNG đóng hẳn (0.18-0.25) = mắt lờ đờ
        - Chớp mắt RẤT ÍT trong 10 giây (< 3 lần)
        - Đầu nghiêng/cúi
        - Nhìn thẳng nhưng không tập trung
        - Neutral emotion
        
        Args:
            ear_avg: Eye Aspect Ratio trung bình
            blink_count_last_10s: Số lần chớp mắt trong 10s gần nhất
            head_pitch: Góc cúi đầu
            head_roll: Góc nghiêng đầu
            gaze_direction: Hướng nhìn
            emotion: Cảm xúc
        
        Returns:
            bool: True nếu đang mơ màng
        """
        # 1. Mắt mở nhưng mệt mỏi (EAR thấp nhưng chưa đóng)
        is_tired_eyes = 0.18 < ear_avg < 0.25
        
        # 2. Chớp mắt CỰC ÍT = staring blankly
        is_staring_blankly = blink_count_last_10s < 3
        
        # 3. Đầu nghiêng hoặc cúi nhẹ
        is_head_tilted = abs(head_pitch) > 10 or abs(head_roll) > 8
        
        # 4. Nhìn thẳng nhưng không focus (gaze center + neutral emotion)
        is_unfocused_stare = (
            gaze_direction == "CENTER" and 
            emotion == 'neutral'
        )
        
        # KẾT HỢP: ít nhất 3/4 điều kiện
        dazed_indicators = sum([
            is_tired_eyes,
            is_staring_blankly,
            is_head_tilted,
            is_unfocused_stare
        ])
        
        if dazed_indicators >= 3:
            self.dazed_counter += 1
        else:
            self.dazed_counter = max(0, self.dazed_counter - 2)
            
        if self.dazed_counter >= self.DAZED_THRESHOLD_FRAMES:
            self.is_dazed = True
            return True
        else:
            self.is_dazed = False
            return False
    
    def detect_severe_distraction(self,
                                 gaze_direction: str,
                                 head_yaw: float,
                                 emotion: str,
                                 is_using_phone: bool,
                                 posture_score: float) -> bool:
        """Phát hiện MẤT TẬP TRUNG NGHIÊM TRỌNG
        
        Dấu hiệu:
        - Nhìn đi nơi khác liên tục
        - Quay đầu sang hẳn
        - Emotion: surprise, happy (bị làm phiền)
        - Đang dùng điện thoại
        - Tư thế xấu kéo dài
        
        Args:
            gaze_direction: Hướng nhìn
            head_yaw: Góc quay đầu
            emotion: Cảm xúc
            is_using_phone: Có đang dùng điện thoại?
            posture_score: Điểm tư thế
        
        Returns:
            bool: True nếu mất tập trung nghiêm trọng
        """
        # 1. Nhìn đi chỗ khác (không center)
        is_looking_away = gaze_direction != "CENTER"
        
        # 2. Quay đầu sang hẳn
        is_head_turned = abs(head_yaw) > 30
        
        # 3. Cảm xúc bị làm phiền
        is_distracted_emotion = emotion in ['surprise', 'happy', 'angry']
        
        # 4. Dùng điện thoại
        # is_using_phone (already a boolean)
        
        # 5. Tư thế xấu
        is_bad_posture = posture_score < 40
        
        # KẾT HỢP: ít nhất 2/5 điều kiện (nghiêm trọng hơn)
        severe_indicators = sum([
            is_looking_away,
            is_head_turned,
            is_distracted_emotion,
            is_using_phone,
            is_bad_posture
        ])
        
        if severe_indicators >= 2:
            self.severe_distraction_counter += 1
        else:
            self.severe_distraction_counter = max(0, self.severe_distraction_counter - 3)
            
        if self.severe_distraction_counter >= self.SEVERE_DISTRACTION_FRAMES:
            self.is_severely_distracted = True
            return True
        else:
            self.is_severely_distracted = False
            return False
    
    def update_blink_tracking(self, ear_avg: float, threshold: float = 0.21):
        """Track blink rate để detect dazed state
        
        Args:
            ear_avg: Eye Aspect Ratio
            threshold: EAR threshold để xác định blink
        """
        current_time = time.time()
        
        # Detect blink: EAR giảm xuống dưới threshold
        if ear_avg < threshold:
            # Check nếu đây là blink mới (không phải cùng 1 blink)
            if current_time - self.last_blink_time > 0.2:  # 200ms giữa các blink
                self.blink_count += 1
                self.last_blink_time = current_time
        
        # Reset counter mỗi 10 giây
        if current_time - self.last_blink_time > 10.0:
            self.blink_count = 0
            self.last_blink_time = current_time
    
    def get_blink_count_last_10s(self) -> int:
        """Lấy số lần chớp mắt trong 10s gần nhất"""
        current_time = time.time()
        if current_time - self.last_blink_time > 10.0:
            return 0
        return self.blink_count
    
    def get_blink_rate(self) -> float:
        """Tính blink rate (blinks/minute)"""
        current_time = time.time()
        elapsed = current_time - (self.last_blink_time - 10.0)
        
        if elapsed <= 0:
            return 0.0
        
        # Convert to blinks per minute
        blinks_per_minute = (self.blink_count / elapsed) * 60
        return blinks_per_minute
    
    def process_all_states(self, 
                          ear_avg: float,
                          emotion: str,
                          emotion_conf: float,
                          head_pitch: float,
                          head_roll: float,
                          head_yaw: float,
                          gaze_direction: str,
                          is_using_phone: bool,
                          posture_score: float) -> Dict[str, any]:
        """Xử lý TẤT CẢ trạng thái nâng cao
        
        Returns:
            dict với keys:
            - is_bored
            - is_dazed
            - is_severely_distracted
            - blink_rate
            - dominant_state: 'normal', 'bored', 'dazed', 'distracted'
            - warning_message
        """
        # 1. Update blink tracking
        self.update_blink_tracking(ear_avg)
        blink_rate = self.get_blink_rate()
        blink_count_10s = self.get_blink_count_last_10s()
        
        # 2. Detect từng state
        is_bored = self.detect_boredom(
            emotion, emotion_conf, head_pitch, head_yaw, 
            gaze_direction, blink_rate
        )
        
        is_dazed = self.detect_dazed(
            ear_avg, blink_count_10s, head_pitch, head_roll,
            gaze_direction, emotion
        )
        
        is_severely_distracted = self.detect_severe_distraction(
            gaze_direction, head_yaw, emotion, is_using_phone, posture_score
        )
        
        # 3. Xác định dominant state (ưu tiên: dazed > bored > distracted)
        if is_dazed:
            dominant_state = 'dazed'
            warning = '🌀 MƠ MÀNG - Hãy nghỉ ngơi!'
        elif is_bored:
            dominant_state = 'bored'
            warning = '😴 BUỒN CHÁN - Thử đổi cách học?'
        elif is_severely_distracted:
            dominant_state = 'distracted'
            warning = '⚠️ MẤT TẬP TRUNG NGHIÊM TRỌNG!'
        else:
            dominant_state = 'normal'
            warning = ''
        
        return {
            'is_bored': is_bored,
            'is_dazed': is_dazed,
            'is_severely_distracted': is_severely_distracted,
            'blink_rate': round(blink_rate, 1),
            'blink_count_10s': blink_count_10s,
            'dominant_state': dominant_state,
            'warning_message': warning,
            'boredom_counter': self.boredom_counter,
            'dazed_counter': self.dazed_counter,
            'distraction_counter': self.severe_distraction_counter
        }
    
    def reset(self):
        """Reset tất cả counters"""
        self.boredom_counter = 0
        self.dazed_counter = 0
        self.severe_distraction_counter = 0
        self.is_bored = False
        self.is_dazed = False
        self.is_severely_distracted = False
        self.blink_count = 0
        self.last_blink_time = time.time()
