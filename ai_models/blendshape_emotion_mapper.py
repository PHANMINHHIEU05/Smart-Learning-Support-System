from typing import Dict, Tuple
import math

class BlendshapeEmotionMapper:
    EMOTION_SCORES = {
        'happy': 100,
        'neutral': 85,
        'surprise': 75,
        'fear': 60,
        'sad': 45,
        'angry': 30,
        'disgust': 20
    }
    EMOTION_THRESHOLDS = 0.25
    NEUTRAL_THRESHOLD = 0.20
    def __init__(self):
        self.current_emotion = 'neutral'
        self.emotion_confidence = 85.0
    def map_to_emotion(self, blendshapes: Dict[str , float]) -> Tuple[str , float]:
        if not blendshapes or len(blendshapes) == 0:
            return 'neutral', 85.0
        scores = {
            'happy': self._calculate_happy(blendshapes),
            'sad': self._calculate_sad(blendshapes),
            'surprise': self._calculate_surprise(blendshapes),
            'fear': self._calculate_fear(blendshapes),
            'angry': self._calculate_angry(blendshapes),
            'disgust': self._calculate_disgust(blendshapes)
        }
        max_emotion = max(scores.items(), key = lambda x : x[1])
        dominant_emotion, raw_score = max_emotion
        if raw_score < self.NEUTRAL_THRESHOLD:
            return 'neutral', 85.0 
        confidence = min(100.0 , raw_score * 100)
        if confidence < self.EMOTION_THRESHOLDS * 100:
            return 'neutral', 85.0
        self.current_emotion = dominant_emotion
        self.emotion_confidence = confidence
        return dominant_emotion, confidence
    def _get_blendshape(self, blendshapes: Dict, key : str , default : float) -> float:
        return blendshapes.get(key, default)
    