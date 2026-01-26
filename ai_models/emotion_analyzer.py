from typing import Tuple, Optional, Dict
from deepface import DeepFace
import time

EMOTION_SCORES = {
    'happy': 100,      # Tích cực, hứng thú học
    'neutral': 85,     # Bình thường, tập trung
    'surprise': 75,    # Có thể đang học điều mới
    'fear': 60,        # Lo lắng
    'sad': 45,         # Chán nản, mệt mỏi
    'angry': 30,       # Khó chịu, stress
    'disgust': 20      # Không hứng thú
}
class EmotionAnalyzer:
    """Phân tích cảm xúc từ frame video bằng DeepFace
    
    Lưu ý: DeepFace chậm (~200-500ms), nên chỉ phân tích mỗi N frames
    """
    def __init__(self, analysis_interval: int = 30, confidence_threshold: float = 0.3):
        """
        Args:
            analysis_interval: Số frame giữa các lần phân tích (mặc định 30 ~ 1 giây)
            confidence_threshold: Ngưỡng độ tin cậy tối thiểu
        """
        self.analysis_interval = analysis_interval
        self.confidence_threshold = confidence_threshold
        
        # Trạng thái hiện tại
        self.current_emotion: str = "neutral"
        self.emotion_confidence: float = 0.0
        self.emotion_scores: Dict[str, float] = {}
        self.frame_counter: int = 0
        self.last_analysis_time: float = 0.0

    def should_analyze(self) -> bool:
        """Kiểm tra có nên phân tích frame này không"""
        self.frame_counter += 1
        return self.frame_counter % self.analysis_interval == 0

    def _analyze_with_deepface(self, frame) -> Optional[Dict]:
        try:
            result = DeepFace.analyze(
                img_path=frame,
                actions=['emotion'],
                enforce_detection=False,
                silent=True
            )
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result
        except Exception as e:
            print(f"❌ DeepFace error: {e}")
            return None

    def analyze(self, frame) -> Tuple[str, float, Dict[str, float]]:
        """Phân tích cảm xúc từ frame
        
        Args:
            frame: numpy array (BGR format từ OpenCV)
            
        Returns:
            Tuple[dominant_emotion, confidence, all_emotion_scores]
        """
        if not self.should_analyze():
            return self.current_emotion, self.emotion_confidence, self.emotion_scores
        
        result = self._analyze_with_deepface(frame)
        
        if result is None:
            return self.current_emotion, self.emotion_confidence, self.emotion_scores
        
        # Cập nhật trạng thái
        self.current_emotion = result['dominant_emotion']
        self.emotion_scores = result['emotion']
        self.emotion_confidence = self.emotion_scores[self.current_emotion]
        self.last_analysis_time = time.time()
        
        return self.current_emotion, self.emotion_confidence, self.emotion_scores

    def get_emotion_score(self, emotion: str = None) -> float:
        if emotion is None:
            emotion = self.current_emotion
        return EMOTION_SCORES.get(emotion.lower(), 50.0)

    def get_current_state(self) -> Dict:
        return {
            'emotion': self.current_emotion,
            'confidence': self.emotion_confidence,
            'scores': self.emotion_scores,
            'focus_score': self.get_emotion_score()
        }

    def reset(self):
        self.current_emotion = "neutral"
        self.emotion_confidence = 0.0
        self.emotion_scores = {}
        self.frame_counter = 0