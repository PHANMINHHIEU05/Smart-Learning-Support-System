from typing import Dict
class FocusCalculator:    
    EMOTION_SCORES = {
        'happy': 100, 'neutral': 85, 'surprise': 75,
        'fear': 60, 'sad': 45, 'angry': 30, 'disgust': 20
    }
    
    def __init__(self, 
                 w_ear: float = 0.30,        # Tăng: Drowsiness quan trọng
                 w_posture: float = 0.30,    # Tăng: Posture quan trọng
                 w_emotion: float = 0.10,    # Giảm: Emotion ít quan trọng hơn
                 w_gaze: float = 0.30,       # Tăng: Gaze/distraction quan trọng
                 w_phone: float = 0.0):      # Bỏ: Phone detector đã tắt
        """
        WEIGHTS ĐÃ TỐI ƯU CHO: Tập trung, Buồn ngủ, Tư thế
        
        Args:
            w_ear: Weight cho EAR score (drowsiness) - 30%
            w_posture: Weight cho Posture score - 30%
            w_emotion: Weight cho Emotion score - 10%
            w_gaze: Weight cho Gaze score (distraction) - 30%
            w_phone: Weight cho Phone penalty - 0% (ĐÃ TẮT)
        """
        self.w_ear = w_ear
        self.w_posture = w_posture
        self.w_emotion = w_emotion
        self.w_gaze = w_gaze
        self.w_phone = w_phone
        
        # Lưu điểm từng thành phần để breakdown
        self.last_ear_score = 0.0
        self.last_posture_score = 0.0
        self.last_emotion_score = 0.0
        self.last_gaze_score = 0.0
        self.last_phone_score = 0.0
        self.last_total = 0.0

    def ear_to_score(self, ear_avg: float) -> float:
        """Convert EAR sang điểm 0-100
        
        EAR cao = mắt mở = tỉnh táo
        """
        if ear_avg > 0.25:
            return 100.0
        elif ear_avg > 0.20:
            return 80.0
        elif ear_avg > 0.15:
            return 50.0
        else:
            return 20.0

    def emotion_to_score(self, emotion: str) -> float:
        return self.EMOTION_SCORES.get(emotion.lower(), 50.0)

    def gaze_to_score(self, gaze_ratio: float, is_distracted: bool) -> float:
        if is_distracted:
            return 20.0
        
        center_distance = abs(gaze_ratio - 0.5)
        if center_distance < 0.15:  # CENTER
            return 100.0
        elif center_distance < 0.25:  # Nhìn lệch nhẹ
            return 70.0
        else:  # Nhìn sang bên
            return 40.0

    def phone_penalty(self, is_using_phone: bool) -> float:
        return 0.0 if is_using_phone else 100.0

    def calculate_focus_score(self, 
                              ear_avg: float,
                              posture_score: float,
                              emotion: str = 'neutral',
                              gaze_ratio: float = 0.5,
                              is_distracted: bool = False,
                              is_using_phone: bool = False) -> float:
        self.last_ear_score = self.ear_to_score(ear_avg)
        self.last_posture_score = posture_score
        self.last_emotion_score = self.emotion_to_score(emotion)
        self.last_gaze_score = self.gaze_to_score(gaze_ratio, is_distracted)
        self.last_phone_score = self.phone_penalty(is_using_phone)
        
        # Tính tổng có trọng số
        focus = (
            self.w_ear * self.last_ear_score +
            self.w_posture * self.last_posture_score +
            self.w_emotion * self.last_emotion_score +
            self.w_gaze * self.last_gaze_score +
            self.w_phone * self.last_phone_score
        )
        
        self.last_total = round(max(0, min(100, focus)), 1)
        return self.last_total

    def get_focus_level(self, score: float = None) -> Dict:
        if score is None:
            score = self.last_total
            
        if score >= 90:
            return {'level': 'EXCELLENT', 'emoji': '🟢', 'message': 'Rất tập trung'}
        elif score >= 75:
            return {'level': 'GOOD', 'emoji': '🟢', 'message': 'Tập trung tốt'}
        elif score >= 60:
            return {'level': 'MODERATE', 'emoji': '🟡', 'message': 'Tập trung vừa'}
        elif score >= 40:
            return {'level': 'LOW', 'emoji': '🟠', 'message': 'Phân tâm nhẹ'}
        else:
            return {'level': 'POOR', 'emoji': '🔴', 'message': 'Mất tập trung'}

    def get_detailed_breakdown(self) -> Dict:
        return {
            'scores': {
                'ear': self.last_ear_score,
                'posture': self.last_posture_score,
                'emotion': self.last_emotion_score,
                'gaze': self.last_gaze_score,
                'phone': self.last_phone_score,
            },
            'total': self.last_total,
            'level': self.get_focus_level(),
            'weights': {
                'ear': self.w_ear,
                'posture': self.w_posture,
                'emotion': self.w_emotion,
                'gaze': self.w_gaze,
                'phone': self.w_phone
            }
        }

    def reset(self):
        self.last_ear_score = 0.0
        self.last_posture_score = 0.0
        self.last_emotion_score = 0.0
        self.last_gaze_score = 0.0
        self.last_phone_score = 0.0
        self.last_total = 0.0
