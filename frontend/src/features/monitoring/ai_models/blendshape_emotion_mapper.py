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
    def _calculate_happy(self, bs: Dict) -> float:
        smile_left = self._get_blendshape(bs , 'mouthSmileLeft', 0.0)
        smile_right = self._get_blendshape(bs , 'mouthSmileRight', 0.0)
        cheek_left = self._get_blendshape(bs , 'cheekSquintLeft', 0.0)
        cheek_right = self._get_blendshape(bs , 'cheekSquintRight', 0.0)
        eye_left = self._get_blendshape(bs , 'eyeSquintLeft', 0.0)
        eye_right = self._get_blendshape(bs , 'eyeSquintRight', 0.0)
        smile_avg = (smile_left + smile_right) / 2
        eye_avg = (eye_left + eye_right) / 2
        cheek_avg = (cheek_left + cheek_right) / 2

        score = (
        smile_avg * 0.5 +
        cheek_avg * 0.35 +
        eye_avg * 0.15
        )
        return score
    def _calculate_sad(self, bs: Dict) -> float:
        frown_left = self._get_blendshape(bs , 'mouthFrownLeft', 0.0)
        frown_right = self._get_blendshape(bs , 'mouthFrownRight', 0.0)
        brow_down_left = self._get_blendshape(bs , 'browInnerLeft', 0.0)
        brow_down_right = self._get_blendshape(bs , 'browInnerRight', 0.0)
        brow_inner = self._get_blendshape(bs , 'browInnerUp', 0.0)
        frown_avg = (frown_left + frown_right) / 2
        brow_down_avg = (brow_down_left + brow_down_right) / 2
        score = (
        frown_avg * 0.4 + 
        brow_down_avg * 0.35 +
        brow_inner * 0.25
        )
        return score
    def _calculate_surprise(self, bs: Dict) -> float:
        """
        Surprise: Ngạc nhiên
        - eyeWide: rất cao (mắt mở to)
        - browInnerUp: cao (lông mày nhướng)
        - jawOpen: cao (há miệng)
        - mouthFunnel: cao (miệng tròn)
        """
        eye_left = self._get_blendshape(bs, 'eyeWideLeft', 0.0)
        eye_right = self._get_blendshape(bs, 'eyeWideRight', 0.0)
        brow_inner = self._get_blendshape(bs, 'browInnerUp', 0.0)
        jaw_open = self._get_blendshape(bs, 'jawOpen', 0.0)
        mouth_funnel = self._get_blendshape(bs, 'mouthFunnel', 0.0)

        eye_avg = (eye_left + eye_right) / 2

        score = (
            eye_avg * 0.3 +
            brow_inner * 0.3 +
            jaw_open * 0.2 +
            mouth_funnel * 0.2
        )

        return score

    def _calculate_fear(self, bs: Dict) -> float:
        """
        Fear: Sợ hãi
        - eyeWide: cao (giống surprise)
        - browInnerUp: rất cao
        - mouthStretch: cao (môi căng)
        - Không cười (khác surprise)
        """
        eye_left = self._get_blendshape(bs, 'eyeWideLeft', 0.0)
        eye_right = self._get_blendshape(bs, 'eyeWideRight', 0.0)
        brow_inner = self._get_blendshape(bs, 'browInnerUp', 0.0)
        stretch_left = self._get_blendshape(bs, 'mouthStretchLeft', 0.0)
        stretch_right = self._get_blendshape(bs, 'mouthStretchRight', 0.0)

        # Penalty nếu có smile (fear không cười)
        smile_left = self._get_blendshape(bs, 'mouthSmileLeft', 0.0)
        smile_right = self._get_blendshape(bs, 'mouthSmileRight', 0.0)
        smile_penalty = (smile_left + smile_right) / 2

        eye_avg = (eye_left + eye_right) / 2
        stretch_avg = (stretch_left + stretch_right) / 2

        score = (
            eye_avg * 0.3 +
            brow_inner * 0.4 +
            stretch_avg * 0.3
        ) * (1.0 - smile_penalty * 0.5)  # Giảm score nếu có smile

        return max(0.0, score)

    def _calculate_angry(self, bs: Dict) -> float:
        """
        Angry: Tức giận
        - browDown: rất cao (cau mày mạnh)
        - eyeSquint: cao (nheo mắt)
        - mouthPress: cao (cắn môi)
        - jawForward: có thể cao
        """
        brow_down_left = self._get_blendshape(bs, 'browDownLeft', 0.0)
        brow_down_right = self._get_blendshape(bs, 'browDownRight', 0.0)
        eye_left = self._get_blendshape(bs, 'eyeSquintLeft', 0.0)
        eye_right = self._get_blendshape(bs, 'eyeSquintRight', 0.0)
        press_left = self._get_blendshape(bs, 'mouthPressLeft', 0.0)
        press_right = self._get_blendshape(bs, 'mouthPressRight', 0.0)
        jaw_forward = self._get_blendshape(bs, 'jawForward', 0.0)

        brow_avg = (brow_down_left + brow_down_right) / 2
        eye_avg = (eye_left + eye_right) / 2
        press_avg = (press_left + press_right) / 2

        score = (
            brow_avg * 0.45 +
            eye_avg * 0.25 +
            press_avg * 0.15 +
            jaw_forward * 0.15
        )

        return score

    def _calculate_disgust(self, bs: Dict) -> float:
        """
        Disgust: Ghê tởm
        - mouthUpperUp: cao (nhăn mũi, môi trên nâng)
        - noseSneer: cao (nhăn mũi)
        - cheekSquint: cao (khác với happy - không có smile)
        """
        upper_left = self._get_blendshape(bs, 'mouthUpperUpLeft', 0.0)
        upper_right = self._get_blendshape(bs, 'mouthUpperUpRight', 0.0)
        sneer_left = self._get_blendshape(bs, 'noseSneerLeft', 0.0)
        sneer_right = self._get_blendshape(bs, 'noseSneerRight', 0.0)
        cheek_left = self._get_blendshape(bs, 'cheekSquintLeft', 0.0)
        cheek_right = self._get_blendshape(bs, 'cheekSquintRight', 0.0)

        # Penalty nếu có smile
        smile_left = self._get_blendshape(bs, 'mouthSmileLeft', 0.0)
        smile_right = self._get_blendshape(bs, 'mouthSmileRight', 0.0)
        smile_penalty = (smile_left + smile_right) / 2

        upper_avg = (upper_left + upper_right) / 2
        sneer_avg = (sneer_left + sneer_right) / 2
        cheek_avg = (cheek_left + cheek_right) / 2

        score = (
            upper_avg * 0.4 +
            sneer_avg * 0.4 +
            cheek_avg * 0.2
        ) * (1.0 - smile_penalty * 0.7)  # Giảm mạnh nếu có smile

        return max(0.0, score)

    def get_emotion_score(self, emotion: str = None) -> float:
        """Lấy focus score từ emotion (giống DeepFace)"""
        if emotion is None:
            emotion = self.current_emotion
        return self.EMOTION_SCORES.get(emotion.lower(), 50.0)

    def get_current_state(self) -> Dict:
        """Lấy trạng thái hiện tại"""
        return {
            'emotion': self.current_emotion,
            'confidence': self.emotion_confidence,
            'focus_score': self.get_emotion_score()
        }