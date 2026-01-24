class FocusCalculator:
    """Tính Focus Score từ EAR, Posture và Emotion
    
    Formula: Focus = W1*EAR_Score + W2*Posture_Score + W3*Emotion_Score
    """
    
    EMOTION_SCORES = {
        'happy': 100, 'neutral': 85, 'surprise': 75,
        'fear': 60, 'sad': 45, 'angry': 30, 'disgust': 20
    }
    
    def __init__(self, weight_ear: float = 0.4, weight_posture: float = 0.3,
                 weight_emotion: float = 0.3):
        self.weight_ear = weight_ear
        self.weight_posture = weight_posture
        self.weight_emotion = weight_emotion

    def ear_to_score(self, ear_avg: float) -> float:
        """Convert EAR sang điểm 0-100"""
        if ear_avg > 0.25:
            return 100.0
        elif ear_avg > 0.20:
            return 80.0
        elif ear_avg > 0.15:
            return 50.0
        else:
            return 20.0

    def emotion_to_score(self, emotion: str) -> float:
        """Convert emotion sang điểm 0-100"""
        return self.EMOTION_SCORES.get(emotion.lower(), 50.0)

    def calculate_focus_score(self, ear_avg: float, posture_score: float,
                              emotion: str = 'neutral') -> float:
        """Tính Focus Score tổng hợp (0-100)"""
        ear_score = self.ear_to_score(ear_avg)
        emotion_score = self.emotion_to_score(emotion)
        
        focus = (self.weight_ear * ear_score +
                 self.weight_posture * posture_score +
                 self.weight_emotion * emotion_score)
        
        return round(max(0, min(100, focus)), 1)

    def get_focus_level(self, score: float) -> str:
        """Chuyển điểm sang mức độ tập trung"""
        if score >= 85:
            return "🟢 Rất tập trung"
        elif score >= 70:
            return "🟡 Tập trung"
        elif score >= 50:
            return "🟠 Phân tâm nhẹ"
        else:
            return "🔴 Mất tập trung"
