# 📘 HƯỚNG DẪN THAY THẾ DEEPFACE BẰNG MEDIAPIPE BLENDSHAPES

## 🎯 Mục tiêu

Thay thế DeepFace (chậm 200-500ms) bằng MediaPipe Blendshapes (nhanh 2-3ms) để tăng FPS từ 9 lên 25-30 mà vẫn giữ được emotion detection.

---

## 📚 KIẾN THỨC NỀN TẢNG

### MediaPipe Blendshapes là gì?

**Blendshapes** (hay Face Blend Shapes) là các hệ số mô tả biến dạng khuôn mặt:

- Mỗi blendshape là 1 số từ 0.0 → 1.0
- Giá trị cao = muscle group đó đang co/căng
- MediaPipe có **52 blendshapes** mô tả đầy đủ khuôn mặt

**Ví dụ:**

```
mouthSmileLeft = 0.8    → Miệng cười bên trái (80%)
eyeBlinkLeft = 0.05     → Mắt trái gần như mở hoàn toàn
browInnerUp = 0.6       → Lông mày nhướng lên (surprise/fear)
```

### 52 Blendshapes của MediaPipe

**Nhóm MẮT (Eyes):**

- `eyeBlinkLeft`, `eyeBlinkRight` - Nhắm mắt
- `eyeSquintLeft`, `eyeSquintRight` - Nheo mắt
- `eyeWideLeft`, `eyeWideRight` - Mở to mắt
- `eyeLookDownLeft/Right`, `eyeLookUpLeft/Right` - Hướng nhìn

**Nhóm LÔNG MÀY (Brows):**

- `browDownLeft`, `browDownRight` - Cau mày (angry/sad)
- `browInnerUp` - Nhướng lông mày (surprise/fear)
- `browOuterUpLeft`, `browOuterUpRight` - Nâng lông mày ngoài

**Nhóm MỒM (Mouth):**

- `mouthSmileLeft`, `mouthSmileRight` - Cười
- `mouthFrownLeft`, `mouthFrownRight` - Nhăn mặt (sad)
- `mouthPucker` - Chu môi
- `mouthFunnel` - Tròn miệng (surprise)
- `jawOpen` - Há miệng
- `mouthUpperUpLeft/Right` - Nâng môi trên (disgust)

**Nhóm MÁ (Cheeks):**

- `cheekSquintLeft`, `cheekSquintRight` - Má nhăn lên (smile)
- `cheekPuff` - Phồng má

### Map Blendshapes → 7 Emotions

#### 1. **HAPPY** 😊

**Đặc điểm:**

- Miệng cười (`mouthSmileLeft/Right` cao)
- Má nhăn lên (`cheekSquint` cao)
- Mắt nheo nhẹ (từ cười)

**Công thức:**

```python
happy_score = (
    (mouthSmileLeft + mouthSmileRight) / 2 * 0.5 +
    (cheekSquintLeft + cheekSquintRight) / 2 * 0.3 +
    eyeSquintLeft * 0.1 +
    eyeSquintRight * 0.1
)
# Range: 0.0 - 1.0
```

#### 2. **SAD** 😢

**Đặc điểm:**

- Môi cong xuống (`mouthFrown` cao)
- Lông mày cau (`browDown` cao)
- Lông mày trong nhướng lên (`browInnerUp`)

**Công thức:**

```python
sad_score = (
    (mouthFrownLeft + mouthFrownRight) / 2 * 0.4 +
    (browDownLeft + browDownRight) / 2 * 0.3 +
    browInnerUp * 0.3
)
```

#### 3. **SURPRISE** 😮

**Đặc điểm:**

- Mắt mở to (`eyeWide` cao)
- Lông mày nhướng cao (`browInnerUp` cao)
- Miệng há (`jawOpen`, `mouthFunnel`)

**Công thức:**

```python
surprise_score = (
    (eyeWideLeft + eyeWideRight) / 2 * 0.3 +
    browInnerUp * 0.3 +
    jawOpen * 0.2 +
    mouthFunnel * 0.2
)
```

#### 4. **FEAR** 😨

**Đặc điểm:**

- Mắt mở to + lông mày nhướng (giống surprise)
- Môi căng (`mouthStretch`)
- Không cười (khác surprise)

**Công thức:**

```python
fear_score = (
    (eyeWideLeft + eyeWideRight) / 2 * 0.3 +
    browInnerUp * 0.4 +
    mouthStretchLeft * 0.15 +
    mouthStretchRight * 0.15
)
```

#### 5. **ANGRY** 😠

**Đặc điểm:**

- Lông mày cau mạnh (`browDown` rất cao)
- Mắt nheo (`eyeSquint`)
- Môi căng hoặc cắn (`mouthPress`)

**Công thức:**

```python
angry_score = (
    (browDownLeft + browDownRight) / 2 * 0.5 +
    (eyeSquintLeft + eyeSquintRight) / 2 * 0.3 +
    mouthPressLeft * 0.1 +
    mouthPressRight * 0.1
)
```

#### 6. **DISGUST** 🤢

**Đặc điểm:**

- Môi trên nâng lên (`mouthUpperUp`)
- Mũi nhăn (`noseSneer`)
- Má nhăn (`cheekSquint`)

**Công thức:**

```python
disgust_score = (
    (mouthUpperUpLeft + mouthUpperUpRight) / 2 * 0.4 +
    (noseSneerLeft + noseSneerRight) / 2 * 0.4 +
    (cheekSquintLeft + cheekSquintRight) / 2 * 0.2
)
```

#### 7. **NEUTRAL** 😐

**Đặc điểm:**

- TẤT CẢ blendshapes đều thấp (< 0.3)
- Khuôn mặt thư giãn

**Công thức:**

```python
# Nếu TẤT CẢ emotions khác < 0.3 → NEUTRAL
all_emotions_low = max(happy, sad, surprise, fear, angry, disgust) < 0.3
if all_emotions_low:
    emotion = 'neutral'
```

---

## 🔧 IMPLEMENTATION - BƯỚC 1: Tắt DeepFace tạm thời

**Mục tiêu:** Tăng FPS lên 25+ ngay để test

### File: `main.py`

**Tìm dòng 106-111:**

```python
# === EMOTION ANALYSIS (mỗi 30 frames - tối ưu) ===
if self.frame_count % self.EMOTION_CHECK_INTERVAL == 0:
    # Resize frame nhỏ để emotion analysis nhanh hơn
    small_frame = cv2.resize(frame, (224, 224))
    emotion, emotion_conf, _ = self.emotion_analyzer.analyze(small_frame)
    self.last_emotion_result = (emotion, emotion_conf, None)
else:
    emotion, emotion_conf, _ = self.last_emotion_result
```

**Thay bằng:**

```python
# === EMOTION ANALYSIS - TẠM THỜI TẮT DEEPFACE ===
# TODO: Sẽ thay bằng MediaPipe Blendshapes
emotion = 'neutral'
emotion_conf = 85.0
self.last_emotion_result = (emotion, emotion_conf, None)
```

**Test:**

```bash
python main.py
# FPS nên tăng lên ~25-28 ngay!
```

---

## 🔧 IMPLEMENTATION - BƯỚC 2: Thêm Blendshapes vào Face Mesh

⚠️ **LƯU Ý QUAN TRỌNG:**

MediaPipe có **2 APIs khác nhau**:

1. **`mediapipe.solutions`** (đang dùng) - KHÔNG hỗ trợ blendshapes
2. **`mediapipe.tasks.python`** (mới) - CÓ blendshapes

→ **PHẢI CHUYỂN SANG API MỚI!**

### File: `core/ai_processor.py`

**Step 2.1: Import thư viện mới**

**Thay đổi imports (dòng 1-10):**

```python
import cv2
import threading
import time
import numpy as np
.
# THÊM MỚI: MediaPipe Tasks API
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import Optional, Dict

from ai_models.drowsiness_detector import DrowsinessDetector
from ai_models.posture_analyzer import PostureAnalyzer
from ai_models.focus_calculator import FocusCalculator
```

**Step 2.2: Download Face Landmarker Model**

MediaPipe Tasks cần file model `.task`:

```bash
# Trong terminal
cd /home/phanhieu/Documents/MyProject_web/Smart-Learning-Support-System

# Download model (5.6MB)
wget -O face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

# Tạo thư mục models
mkdir -p models
mv face_landmarker.task models/
```

**Step 2.3: Khởi tạo Face Landmarker với Blendshapes**

**Thay đổi `_init_models()` method (dòng 42-66):**

```python
def _init_models(self) -> bool:
    try:
        print("🔄 Đang khởi tạo AI models...")

        # === MEDIAPIPE FACE LANDMARKER với BLENDSHAPES ===
        base_options = python.BaseOptions(
            model_asset_path='models/face_landmarker.task'
        )

        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,  # ← KEY: Bật blendshapes!
            output_facial_transformation_matrixes=False,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.face_landmarker = vision.FaceLandmarker.create_from_options(options)

        # === MEDIAPIPE POSE (giữ nguyên) ===
        # Import solutions cho Pose (vì Tasks API chưa có Pose)
        import mediapipe as mp
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            enable_segmentation=False
        )

        # === AI DETECTORS ===
        self.drowsiness_detector = DrowsinessDetector()
        self.posture_analyzer = PostureAnalyzer()
        self.focus_calculator = FocusCalculator()

        print("✅ AI models khởi tạo thành công (với Blendshapes!)")
        return True
    except Exception as e:
        print(f"❌ Lỗi khởi tạo AI models: {e}")
        import traceback
        traceback.print_exc()
        return False
```

**Step 2.4: Sửa `_process_frame()` để xử lý API mới**

**Thay đổi phần Face detection (dòng 72-80):**

```python
def _process_frame(self, frame) -> Optional[Dict]:
    try:
        # Resize frame cho processing
        h, w = frame.shape[:2]
        scale = 320 / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        frame_small = cv2.resize(frame, (new_w, new_h))

        # Convert BGR → RGB cho MediaPipe
        frame_rgb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)

        # === FACE LANDMARKER (API mới) ===
        # Phải convert sang MediaPipe Image format
        mp_image = python.vision.Image(
            image_format=python.vision.ImageFormat.SRGB,
            data=frame_rgb
        )

        # Detect face + blendshapes
        face_result = self.face_landmarker.detect(mp_image)

        # Extract landmarks và blendshapes
        face_landmarks = None
        blendshapes_dict = {}

        if face_result.face_landmarks and len(face_result.face_landmarks) > 0:
            # Landmarks (để tương thích với code cũ)
            # MediaPipe Tasks trả về list, cần convert sang format cũ
            face_landmarks = self._convert_landmarks(face_result.face_landmarks[0])

            # Blendshapes
            if face_result.face_blendshapes and len(face_result.face_blendshapes) > 0:
                blendshapes_list = face_result.face_blendshapes[0]
                # Convert thành dict: {'mouthSmileLeft': 0.8, ...}
                blendshapes_dict = {
                    bs.category_name: bs.score
                    for bs in blendshapes_list
                }

        # === POSE DETECTION (giữ nguyên) ===
        pose_results = self.pose.process(frame_rgb)

        # === XỬ LÝ TIẾP (giữ nguyên phần drowsiness, posture...) ===
        ear_left, ear_right, is_drowsy = 0.0, 0.0, False
        if face_landmarks is not None:
            ear_left, ear_right, is_drowsy = self.drowsiness_detector.process(face_landmarks)
        ear_avg = (ear_left + ear_right) / 2.0

        # Posture analysis
        head_tilt, shoulder_angle, posture_score, is_bad_posture = 0.0, 0.0, 100.0, False
        if pose_results.pose_landmarks:
            head_tilt, shoulder_angle, posture_score, is_bad_posture = \
                self.posture_analyzer.process(pose_results.pose_landmarks, face_landmarks)

        # Face distance
        face_distance_ipd = 0.15
        if face_landmarks is not None:
            face_distance_ipd = self.posture_analyzer.calculate_face_distance(face_landmarks)

        posture_details = self.posture_analyzer.get_posture_details()

        focus_score = self.focus_calculator.calculate_focus_score(
            ear_avg=ear_avg,
            posture_score=posture_score,
            emotion=self.current_emotion
        )

        return {
            'timestamp': time.time(),
            'ear_left': round(ear_left, 3),
            'ear_right': round(ear_right, 3),
            'ear_avg': round(ear_avg, 3),
            'head_tilt': round(head_tilt, 2),
            'shoulder_angle': round(shoulder_angle, 2),
            'posture_score': round(posture_score, 2),
            'face_distance_ipd': round(face_distance_ipd, 3),
            'posture_details': posture_details,
            'emotion': self.current_emotion,
            'emotion_confidence': round(self.emotion_confidence, 2),
            'focus_score': focus_score,
            'is_drowsy': is_drowsy,
            'is_bad_posture': is_bad_posture,
            'face_landmarks': face_landmarks,
            'blendshapes': blendshapes_dict,  # ← THÊM MỚI
            'frame': frame
        }
    except Exception as e:
        print(f"❌ Lỗi xử lý frame: {e}")
        import traceback
        traceback.print_exc()
        return None

def _convert_landmarks(self, new_landmarks):
    """Convert MediaPipe Tasks landmarks → format cũ để tương thích"""
    # Tạo object giống mp.solutions.face_mesh.FaceLandmark
    class LandmarkList:
        def __init__(self, landmarks):
            self.landmark = landmarks

    class Landmark:
        def __init__(self, x, y, z):
            self.x = x
            self.y = y
            self.z = z

    # Convert
    converted = [
        Landmark(lm.x, lm.y, lm.z)
        for lm in new_landmarks
    ]

    return LandmarkList(converted)
```

---

## 🔧 IMPLEMENTATION - BƯỚC 3: Tạo Blendshape → Emotion Mapper

### File: `ai_models/blendshape_emotion_mapper.py` (TẠO MỚI)

```python
"""
Blendshape Emotion Mapper
Map 52 MediaPipe blendshapes → 7 emotions (happy, sad, surprise, fear, angry, disgust, neutral)
"""

from typing import Dict, Tuple
import math


class BlendshapeEmotionMapper:
    """Map MediaPipe face blendshapes to emotions"""

    # Emotion scores (giống DeepFace)
    EMOTION_SCORES = {
        'happy': 100,
        'neutral': 85,
        'surprise': 75,
        'fear': 60,
        'sad': 45,
        'angry': 30,
        'disgust': 20
    }

    # Thresholds
    EMOTION_THRESHOLD = 0.25  # Điểm tối thiểu để xác định emotion
    NEUTRAL_THRESHOLD = 0.20  # Nếu tất cả < threshold này → neutral

    def __init__(self):
        self.current_emotion = 'neutral'
        self.emotion_confidence = 85.0

    def map_to_emotion(self, blendshapes: Dict[str, float]) -> Tuple[str, float]:
        """
        Map blendshapes dict → (dominant_emotion, confidence)

        Args:
            blendshapes: Dict với keys là tên blendshape, values là scores 0-1

        Returns:
            (emotion_name, confidence_percentage)
        """
        if not blendshapes or len(blendshapes) == 0:
            return 'neutral', 85.0

        # Tính score cho từng emotion
        scores = {
            'happy': self._calculate_happy(blendshapes),
            'sad': self._calculate_sad(blendshapes),
            'surprise': self._calculate_surprise(blendshapes),
            'fear': self._calculate_fear(blendshapes),
            'angry': self._calculate_angry(blendshapes),
            'disgust': self._calculate_disgust(blendshapes)
        }

        # Tìm emotion có score cao nhất
        max_emotion = max(scores.items(), key=lambda x: x[1])
        dominant_emotion, raw_score = max_emotion

        # Nếu TẤT CẢ scores thấp → NEUTRAL
        if raw_score < self.NEUTRAL_THRESHOLD:
            return 'neutral', 85.0

        # Convert score 0-1 → confidence 0-100
        confidence = min(100.0, raw_score * 100)

        # Threshold minimum
        if confidence < self.EMOTION_THRESHOLD * 100:
            return 'neutral', 85.0

        self.current_emotion = dominant_emotion
        self.emotion_confidence = confidence

        return dominant_emotion, confidence

    def _get_blendshape(self, blendshapes: Dict, key: str, default: float = 0.0) -> float:
        """Helper: Lấy blendshape value với default"""
        return blendshapes.get(key, default)

    def _calculate_happy(self, bs: Dict) -> float:
        """
        Happy: Cười
        - mouthSmile: cao (>0.5)
        - cheekSquint: cao (má nhăn lên)
        - eyeSquint: nhẹ (từ cười)
        """
        smile_left = self._get_blendshape(bs, 'mouthSmileLeft')
        smile_right = self._get_blendshape(bs, 'mouthSmileRight')
        cheek_left = self._get_blendshape(bs, 'cheekSquintLeft')
        cheek_right = self._get_blendshape(bs, 'cheekSquintRight')
        eye_left = self._get_blendshape(bs, 'eyeSquintLeft')
        eye_right = self._get_blendshape(bs, 'eyeSquintRight')

        smile_avg = (smile_left + smile_right) / 2
        cheek_avg = (cheek_left + cheek_right) / 2
        eye_avg = (eye_left + eye_right) / 2

        # Weighted combination
        score = (
            smile_avg * 0.5 +
            cheek_avg * 0.35 +
            eye_avg * 0.15
        )

        return score

    def _calculate_sad(self, bs: Dict) -> float:
        """
        Sad: Buồn
        - mouthFrown: cao
        - browDown: cao (cau mày)
        - browInnerUp: cao (nhăn trán)
        """
        frown_left = self._get_blendshape(bs, 'mouthFrownLeft')
        frown_right = self._get_blendshape(bs, 'mouthFrownRight')
        brow_down_left = self._get_blendshape(bs, 'browDownLeft')
        brow_down_right = self._get_blendshape(bs, 'browDownRight')
        brow_inner = self._get_blendshape(bs, 'browInnerUp')

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
        eye_left = self._get_blendshape(bs, 'eyeWideLeft')
        eye_right = self._get_blendshape(bs, 'eyeWideRight')
        brow_inner = self._get_blendshape(bs, 'browInnerUp')
        jaw_open = self._get_blendshape(bs, 'jawOpen')
        mouth_funnel = self._get_blendshape(bs, 'mouthFunnel')

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
        eye_left = self._get_blendshape(bs, 'eyeWideLeft')
        eye_right = self._get_blendshape(bs, 'eyeWideRight')
        brow_inner = self._get_blendshape(bs, 'browInnerUp')
        stretch_left = self._get_blendshape(bs, 'mouthStretchLeft')
        stretch_right = self._get_blendshape(bs, 'mouthStretchRight')

        # Penalty nếu có smile (fear không cười)
        smile_left = self._get_blendshape(bs, 'mouthSmileLeft')
        smile_right = self._get_blendshape(bs, 'mouthSmileRight')
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
        brow_down_left = self._get_blendshape(bs, 'browDownLeft')
        brow_down_right = self._get_blendshape(bs, 'browDownRight')
        eye_left = self._get_blendshape(bs, 'eyeSquintLeft')
        eye_right = self._get_blendshape(bs, 'eyeSquintRight')
        press_left = self._get_blendshape(bs, 'mouthPressLeft')
        press_right = self._get_blendshape(bs, 'mouthPressRight')
        jaw_forward = self._get_blendshape(bs, 'jawForward')

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
        upper_left = self._get_blendshape(bs, 'mouthUpperUpLeft')
        upper_right = self._get_blendshape(bs, 'mouthUpperUpRight')
        sneer_left = self._get_blendshape(bs, 'noseSneerLeft')
        sneer_right = self._get_blendshape(bs, 'noseSneerRight')
        cheek_left = self._get_blendshape(bs, 'cheekSquintLeft')
        cheek_right = self._get_blendshape(bs, 'cheekSquintRight')

        # Penalty nếu có smile
        smile_left = self._get_blendshape(bs, 'mouthSmileLeft')
        smile_right = self._get_blendshape(bs, 'mouthSmileRight')
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
```

---

## 🔧 IMPLEMENTATION - BƯỚC 4: Tích hợp vào main.py

### File: `main.py`

**Thêm import (dòng 9):**

```python
from ai_models.blendshape_emotion_mapper import BlendshapeEmotionMapper
```

**Khởi tạo trong `__init__` (dòng 24):**

```python
self.advanced_state_detector = AdvancedStateDetector()
self.blendshape_mapper = BlendshapeEmotionMapper()  # ← THÊM MỚI
self.calibrator = Calibrator()
```

**Thay đổi trong `process_frame()` (dòng 106-111):**

```python
# === EMOTION ANALYSIS - MediaPipe Blendshapes ===
blendshapes = ai_result.get('blendshapes', {})
if blendshapes:
    emotion, emotion_conf = self.blendshape_mapper.map_to_emotion(blendshapes)
else:
    emotion, emotion_conf = 'neutral', 85.0
```

**Xóa phần DeepFace cũ hoàn toàn:**

```python
# XÓA:
# if self.frame_count % self.EMOTION_CHECK_INTERVAL == 0:
#     small_frame = cv2.resize(frame, (224, 224))
#     emotion, emotion_conf, _ = self.emotion_analyzer.analyze(small_frame)
#     self.last_emotion_result = (emotion, emotion_conf, None)
# else:
#     emotion, emotion_conf, _ = self.last_emotion_result
```

---

## 🧪 TESTING & CALIBRATION

### Test 1: Kiểm tra FPS

```bash
python main.py
# Quan sát FPS ở góc phải trên
# Expected: 25-30 FPS (không giảm khi emotion detection chạy)
```

### Test 2: Kiểm tra Emotions

Làm các biểu cảm và quan sát:

1. **HAPPY** 😊 - Cười toe → nên hiện "happy"
2. **SAD** 😢 - Cau mày, nhăn trán → "sad"
3. **SURPRISE** 😮 - Mắt mở to, há miệng → "surprise"
4. **ANGRY** 😠 - Cau mày mạnh, nheo mắt → "angry"
5. **DISGUST** 🤢 - Nhăn mũi, nâng môi trên → "disgust"
6. **FEAR** 😨 - Giống surprise nhưng căng thẳng → "fear"
7. **NEUTRAL** 😐 - Mặt thư giãn → "neutral"

### Test 3: Debug Blendshapes

Thêm print để xem raw blendshapes:

```python
# Trong main.py process_frame()
blendshapes = ai_result.get('blendshapes', {})
if blendshapes:
    # Debug: In top 5 blendshapes cao nhất
    sorted_bs = sorted(blendshapes.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"Top blendshapes: {sorted_bs}")

    emotion, emotion_conf = self.blendshape_mapper.map_to_emotion(blendshapes)
```

### Calibration: Điều chỉnh Thresholds

Nếu emotion detection không chính xác:

**1. Quá nhiều "neutral"** → Giảm `NEUTRAL_THRESHOLD`:

```python
# blendshape_emotion_mapper.py
NEUTRAL_THRESHOLD = 0.15  # Từ 0.20 → 0.15
```

**2. Emotion nhảy liên tục** → Tăng `EMOTION_THRESHOLD`:

```python
EMOTION_THRESHOLD = 0.30  # Từ 0.25 → 0.30
```

**3. Happy quá nhạy** → Giảm weight của cheekSquint:

```python
# _calculate_happy()
score = (
    smile_avg * 0.6 +      # Tăng
    cheek_avg * 0.25 +     # Giảm
    eye_avg * 0.15
)
```

**4. Sad không nhận** → Tăng weight của browInnerUp:

```python
# _calculate_sad()
score = (
    frown_avg * 0.35 +     # Giảm
    brow_down_avg * 0.30 + # Giảm
    brow_inner * 0.35      # Tăng
)
```

---

## 📊 SO SÁNH: DeepFace vs Blendshapes

| Metric           | DeepFace           | Blendshapes        |
| ---------------- | ------------------ | ------------------ |
| **Tốc độ**       | 200-500ms          | 2-3ms              |
| **FPS Impact**   | Giảm 9-12 FPS      | Không giảm         |
| **Accuracy**     | 85-90%             | 65-75%             |
| **Latency**      | High (block)       | None               |
| **Offline**      | ✅                 | ✅                 |
| **Dependencies** | TensorFlow (large) | MediaPipe (có sẵn) |
| **Model size**   | ~100MB             | ~5MB               |
| **7 Emotions**   | ✅                 | ✅                 |
| **Realtime**     | ❌                 | ✅                 |

**Kết luận:** Blendshapes tốt hơn cho real-time monitoring!

---

## 🐛 TROUBLESHOOTING

### Lỗi 1: "No module named 'mediapipe.tasks'"

```bash
# Cài đặt MediaPipe version mới nhất
pip install --upgrade mediapipe
# Hoặc
pip install mediapipe>=0.10.0
```

### Lỗi 2: "model_asset_path not found"

```bash
# Kiểm tra file model tồn tại
ls -lh models/face_landmarker.task

# Nếu không có, download lại:
wget -O models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

### Lỗi 3: "AttributeError: 'NoneType' has no attribute 'face_landmarks'"

```python
# Trong _process_frame(), thêm check:
if face_result.face_landmarks is None or len(face_result.face_landmarks) == 0:
    face_landmarks = None
    blendshapes_dict = {}
```

### Lỗi 4: FPS vẫn thấp

```python
# Giảm resolution processing xuống 240p:
scale = 240 / max(h, w)  # Từ 320 → 240

# Hoặc skip frames:
if self.frame_count % 2 == 0:
    # Process
else:
    # Return cached
```

### Lỗi 5: Emotion detection không chính xác

```python
# Tăng smoothing - lưu history 5 frames:
class BlendshapeEmotionMapper:
    def __init__(self):
        self.emotion_history = []

    def map_to_emotion(self, blendshapes):
        emotion, conf = self._calculate(blendshapes)

        # Smoothing
        self.emotion_history.append(emotion)
        if len(self.emotion_history) > 5:
            self.emotion_history.pop(0)

        # Most common emotion
        from collections import Counter
        dominant = Counter(self.emotion_history).most_common(1)[0][0]

        return dominant, conf
```

---

## ✅ CHECKLIST HOÀN THÀNH

- [ ] **Bước 1:** Comment DeepFace, test FPS (~25)
- [ ] **Bước 2.1:** Import MediaPipe Tasks API
- [ ] **Bước 2.2:** Download face_landmarker.task
- [ ] **Bước 2.3:** Init Face Landmarker với blendshapes
- [ ] **Bước 2.4:** Sửa \_process_frame() xử lý API mới
- [ ] **Bước 3:** Tạo blendshape_emotion_mapper.py
- [ ] **Bước 4:** Tích hợp vào main.py
- [ ] **Test:** FPS 25-30 ổn định
- [ ] **Test:** Emotions detection hoạt động
- [ ] **Calibration:** Điều chỉnh thresholds nếu cần

---

## 🎯 KẾT QUẢ MONG ĐỢI

**TRƯỚC (DeepFace):**

- FPS: 9-12
- Emotion accuracy: 85%
- Latency: 200-500ms
- Experience: Lag, không realtime

**SAU (Blendshapes):**

- FPS: 25-30 ✅
- Emotion accuracy: 70-75%
- Latency: 2-3ms ✅
- Experience: Smooth, realtime ✅

**Trade-off chấp nhận được:**

- Giảm accuracy 10-15% để có FPS cao gấp 3 lần
- Cho mục đích giám sát học tập: ĐỦ TỐT!

---

## 📚 TÀI LIỆU THAM KHẢO

**MediaPipe Documentation:**

- Face Landmarker: https://developers.google.com/mediapipe/solutions/vision/face_landmarker
- Blendshapes list: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png
- Python API: https://developers.google.com/mediapipe/api/solutions/python/mp/tasks/vision

**Model Download:**

- Face Landmarker: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

**Tham khảo thêm:**

- ARKit Blendshapes: https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation
- Facial Action Coding System (FACS): https://en.wikipedia.org/wiki/Facial_Action_Coding_System
