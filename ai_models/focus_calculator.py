from typing import Optional
class FocusCalculator:
    """
    Tính Focus Score dựa trên:
    - EAR (Eye Aspect Ratio)
    - Posture Score
    - Emotion
    Formula:
    Focus = W1*EAR_Score + W2*Posture_Score + W3*Emotion_Score
    """
    # Trọng số mặc định
    WEIGHT_EAR = 0.4      # 40%
    WEIGHT_POSTURE = 0.3  # 30%
    WEIGHT_EMOTION = 0.3  # 30%
    
    # Emotion mapping
    EMOTION_SCORES = {
        'happy': 100,
        'neutral': 85,
        'surprise': 75,
        'fear': 60,
        'sad': 45,
        'angry': 30,
        'disgust': 20
    }
    
    def __init__(self, weight_ear: float = 0.4, 
                 weight_posture: float = 0.3,
                 weight_emotion: float = 0.3):
        """
        Khởi tạo Focus Calculator
        
        Args:
            weight_ear: Trọng số EAR
            weight_posture: Trọng số posture
            weight_emotion: Trọng số emotion
        """
        self.weight_ear = weight_ear
        self.weight_posture = weight_posture
        self.weight_emotion = weight_emotion
    
    def ear_to_score(self, ear_avg: float) -> float:
        """
        Convert EAR value sang điểm (0-100)
        
        Args:
            ear_avg: EAR trung bình
        
        Returns:
            float: Điểm EAR (0-100)
        """
        if ear_avg > 0.25:
            # Mắt mở to → Tỉnh táo
            return 100.0
        elif ear_avg > 0.20:
            # Bình thường
            return 80.0
        elif ear_avg > 0.15:
            # Hơi buồn ngủ
            return 50.0
        else:
            # Rất buồn ngủ
            return 20.0
    
    def emotion_to_score(self, emotion: Optional[str]) -> float:
        """
        Convert emotion sang điểm (0-100)
        
        Args:
            emotion: Cảm xúc (happy, sad, neutral...)
        
        Returns:
            float: Điểm emotion (0-100)
        """
        if emotion is None:
            return 80.0  # Mặc định neutral
        
        emotion_lower = emotion.lower()
        return self.EMOTION_SCORES.get(emotion_lower, 80.0)
    
    def calculate_focus_score(self, ear_avg: float, 
                             posture_score: float,
                             emotion: Optional[str] = None) -> float:
        """
        Tính Focus Score tổng hợp
        
        Args:
            ear_avg: EAR trung bình (0.0 - 0.4)
            posture_score: Điểm tư thế (0-100)
            emotion: Cảm xúc (optional)
        
        Returns:
            float: Focus Score (0-100)
        """
        # Convert EAR sang điểm
        ear_score = self.ear_to_score(ear_avg)
        
        # Convert emotion sang điểm
        emotion_score = self.emotion_to_score(emotion)
        
        # Tính tổng hợp
        focus_score = (
            self.weight_ear * ear_score +
            self.weight_posture * posture_score +
            self.weight_emotion * emotion_score
        )
        
        # Clamp [0, 100]
        focus_score = max(0.0, min(100.0, focus_score))
        
        return round(focus_score, 2)
    
    def get_focus_level(self, focus_score: float) -> str:
        """
        Phân loại mức độ tập trung
        
        Args:
            focus_score: Điểm focus (0-100)
        
        Returns:
            str: Level (Excellent, Good, Fair, Poor)
        """
        if focus_score >= 85:
            return "Excellent"
        elif focus_score >= 70:
            return "Good"
        elif focus_score >= 50:
            return "Fair"
        else:
            return "Poor"