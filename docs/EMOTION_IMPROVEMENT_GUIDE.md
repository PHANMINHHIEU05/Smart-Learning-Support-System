# 🎭 HƯỚNG DẪN CẢI THIỆN EMOTION DETECTION

## 📊 VẤN ĐỀ HIỆN TẠI

**DeepFace** đang dùng chỉ phát hiện 7 cảm xúc cơ bản:

- ✅ `happy`, `sad`, `angry`, `fear`, `surprise`, `disgust`, `neutral`

**Nhưng KHÔNG phát hiện được:**

- ❌ Chán nản (boredom)
- ❌ Lờ đờ (confused/dazed)
- ❌ Mất tập trung (distracted)

---

## 🧠 GIẢI PHÁP: KẾT HỢP MULTIPLE METRICS

### Chiến lược:

**Không chỉ dựa vào emotion**, mà kết hợp với:

1. **EAR (Eye Aspect Ratio)** - Độ mở mắt
2. **Gaze Direction** - Hướng nhìn
3. **Blink Rate** - Tần suất chớp mắt
4. **Head Pose** - Tư thế đầu
5. **Facial Micro-expressions** - Vi biểu cảm

---

## 🎯 PHÁT HIỆN TRẠNG THÁI PHỨC TẠP

### 1️⃣ **CHÁN NẢN (Boredom)**

**Đặc điểm:**

- Mắt mở vừa phải, không buồn ngủ
- Nhìn lệch (không nhìn màn hình)
- Đầu tựa hoặc ngả về một bên
- Emotion: neutral hoặc sad
- Blink rate: bình thường hoặc thấp

**Cách phát hiện:**

**Vị trí:** `ai_models/focus_calculator.py` hoặc tạo file mới `ai_models/advanced_state_detector.py`

```python
def detect_boredom(self,
                   emotion: str,
                   gaze_direction: str,
                   ear_avg: float,
                   head_pitch: float,
                   head_roll: float,
                   is_distracted: bool) -> Tuple[bool, float]:
    """
    Phát hiện trạng thái chán nản

    Returns:
        (is_bored, confidence_score)
    """
    boredom_score = 0.0

    # 1. Emotion neutral hoặc sad (30 điểm)
    if emotion in ['neutral', 'sad']:
        boredom_score += 30

    # 2. Nhìn lệch (không tập trung) (25 điểm)
    if gaze_direction != 'CENTER' or is_distracted:
        boredom_score += 25

    # 3. Đầu nghiêng hoặc tựa (20 điểm)
    if abs(head_roll) > 10 or abs(head_pitch) > 15:
        boredom_score += 20

    # 4. Mắt mở bình thường (không buồn ngủ) (15 điểm)
    if 0.20 < ear_avg < 0.30:
        boredom_score += 15

    # 5. Liên tục distracted (10 điểm)
    if is_distracted:
        boredom_score += 10

    is_bored = boredom_score >= 60  # Ngưỡng 60/100
    confidence = min(100, boredom_score)

    return is_bored, confidence
```

**Ngưỡng:**

- `< 40`: Không chán
- `40-60`: Có thể chán
- `> 60`: Chắc chắn chán

---

### 2️⃣ **LỜ ĐỜ / CONFUSED (Dazed/Confused)**

**Đặc điểm:**

- Mắt mở to (EAR cao bất thường)
- Nhìn thẳng nhưng "trống rỗng" (không chớp mắt)
- Đầu hơi ngả ra sau (head_pitch âm)
- Emotion: surprise hoặc neutral
- Blink rate: CỰC THẤP (< 5 blinks/phút)

**Cách phát hiện:**

```python
def detect_dazed(self,
                 emotion: str,
                 ear_avg: float,
                 blink_count_per_minute: int,
                 head_pitch: float,
                 gaze_ratio: float) -> Tuple[bool, float]:
    """
    Phát hiện trạng thái lờ đờ/confused

    Đặc điểm: Mắt mở to, không chớp, nhìn thẳng nhưng "trống"
    """
    dazed_score = 0.0

    # 1. Mắt mở to bất thường (30 điểm)
    if ear_avg > 0.30:
        dazed_score += 30

    # 2. Tần suất chớp mắt CỰC THẤP (25 điểm)
    if blink_count_per_minute < 8:  # Bình thường: 15-20 blinks/phút
        dazed_score += 25

    # 3. Nhìn thẳng (gaze center) (20 điểm)
    if 0.4 < gaze_ratio < 0.6:
        dazed_score += 20

    # 4. Đầu hơi ngả ra sau (15 điểm)
    if head_pitch < -5:  # Âm = ngẩng đầu
        dazed_score += 15

    # 5. Emotion surprise/neutral (10 điểm)
    if emotion in ['surprise', 'neutral']:
        dazed_score += 10

    is_dazed = dazed_score >= 55
    confidence = min(100, dazed_score)

    return is_dazed, confidence
```

**Cần thêm:** Blink Counter (hiện tại chưa có)

---

### 3️⃣ **MẤT TẬP TRUNG (Distracted)**

**Đặc điểm:**

- Nhìn lệch liên tục
- Đầu quay nhiều
- Emotion: bất kỳ
- Posture xấu

**Cách phát hiện:**

```python
def detect_distracted(self,
                     gaze_direction: str,
                     is_distracted_flag: bool,
                     head_yaw: float,
                     posture_score: float,
                     distraction_duration: float) -> Tuple[bool, float]:
    """
    Phát hiện mất tập trung

    Đặc điểm: Nhìn lệch, quay đầu nhiều, tư thế xấu
    """
    distraction_score = 0.0

    # 1. GazeTracker đã phát hiện distracted (40 điểm)
    if is_distracted_flag:
        distraction_score += 40

    # 2. Đầu quay sang bên (30 điểm)
    if abs(head_yaw) > 20:
        distraction_score += 30

    # 3. Tư thế xấu (15 điểm)
    if posture_score < 50:
        distraction_score += 15

    # 4. Thời gian distracted lâu (15 điểm)
    if distraction_duration > 3.0:  # > 3 giây
        distraction_score += 15

    is_distracted_severe = distraction_score >= 60
    confidence = min(100, distraction_score)

    return is_distracted_severe, confidence
```

---

## 🛠️ CÁCH THỰC HIỆN

### Bước 1: Tạo file mới `ai_models/advanced_state_detector.py`

```python
from typing import Tuple, Dict

class AdvancedStateDetector:
    """Phát hiện trạng thái phức tạp: chán nản, lờ đờ, mất tập trung"""

    def __init__(self):
        self.blink_counter = 0
        self.blink_timestamps = []
        self.distraction_start_time = None

    def update_blink(self, is_blinking: bool):
        """Cập nhật blink counter"""
        import time
        if is_blinking:
            self.blink_counter += 1
            self.blink_timestamps.append(time.time())

        # Xóa blinks cũ hơn 60 giây
        current_time = time.time()
        self.blink_timestamps = [t for t in self.blink_timestamps
                                 if current_time - t < 60]

    def get_blink_rate(self) -> int:
        """Lấy tần suất chớp mắt (blinks/phút)"""
        return len(self.blink_timestamps)

    def detect_boredom(self, ...) -> Tuple[bool, float]:
        # Code như trên
        pass

    def detect_dazed(self, ...) -> Tuple[bool, float]:
        # Code như trên
        pass

    def detect_distracted(self, ...) -> Tuple[bool, float]:
        # Code như trên
        pass

    def get_overall_state(self, ...) -> Dict:
        """Trả về trạng thái tổng hợp"""
        is_bored, bored_conf = self.detect_boredom(...)
        is_dazed, dazed_conf = self.detect_dazed(...)
        is_distracted, dist_conf = self.detect_distracted(...)

        # Ưu tiên: dazed > bored > distracted
        if is_dazed and dazed_conf > 60:
            return {'state': 'DAZED', 'confidence': dazed_conf}
        elif is_bored and bored_conf > 60:
            return {'state': 'BORED', 'confidence': bored_conf}
        elif is_distracted and dist_conf > 60:
            return {'state': 'DISTRACTED', 'confidence': dist_conf}
        else:
            return {'state': 'FOCUSED', 'confidence': 80}
```

---

### Bước 2: Thêm vào `main.py`

```python
from ai_models.advanced_state_detector import AdvancedStateDetector

class MainApplication:
    def __init__(self, ...):
        # ... existing code ...
        self.state_detector = AdvancedStateDetector()  # THÊM MỚI
```

---

### Bước 3: Cập nhật `process_frame()` trong `main.py`

```python
def process_frame(self, ai_result: dict, frame) -> dict:
    # ... existing code ...

    # Lấy thêm metrics
    head_pitch = ai_result.get('head_pitch', 0.0)  # Cần thêm vào ai_processor
    head_roll = ai_result.get('head_roll', 0.0)
    head_yaw = self.gaze_tracker.current_head_yaw  # Nếu có

    # Update blink counter
    is_blinking = ai_result.get('is_blinking', False)  # Cần thêm vào drowsiness_detector
    self.state_detector.update_blink(is_blinking)
    blink_rate = self.state_detector.get_blink_rate()

    # Detect advanced states
    is_bored, bored_conf = self.state_detector.detect_boredom(
        emotion=emotion,
        gaze_direction=gaze_dir,
        ear_avg=ear_avg,
        head_pitch=head_pitch,
        head_roll=head_roll,
        is_distracted=is_distracted
    )

    is_dazed, dazed_conf = self.state_detector.detect_dazed(
        emotion=emotion,
        ear_avg=ear_avg,
        blink_count_per_minute=blink_rate,
        head_pitch=head_pitch,
        gaze_ratio=gaze_ratio
    )

    overall_state = self.state_detector.get_overall_state(...)

    return {
        **ai_result,
        # ... existing fields ...
        'is_bored': is_bored,
        'bored_confidence': bored_conf,
        'is_dazed': is_dazed,
        'dazed_confidence': dazed_conf,
        'overall_state': overall_state['state'],
        'state_confidence': overall_state['confidence'],
        'blink_rate': blink_rate
    }
```

---

### Bước 4: Cập nhật `draw_overlay()` để hiển thị

```python
def draw_overlay(self, frame, data: dict):
    # ... existing code ...

    # Thêm vào info list:
    overall_state = data.get('overall_state', 'FOCUSED')
    state_conf = data.get('state_confidence', 0)

    # Thêm màu theo state
    state_colors = {
        'FOCUSED': (0, 255, 0),    # Xanh
        'DISTRACTED': (0, 255, 255), # Vàng
        'BORED': (0, 165, 255),      # Cam
        'DAZED': (0, 0, 255)         # Đỏ
    }
    state_color = state_colors.get(overall_state, (255, 255, 255))

    # Thêm vào text info
    info = [
        f"State: {overall_state} ({state_conf:.0f}%)",
        # ... existing fields ...
    ]

    # Vẽ với màu riêng cho state
```

---

## 📋 CHECKLIST THỰC HIỆN

### Phase 1: Blink Detection (Cần thiết cho DAZED)

- [ ] Sửa `drowsiness_detector.py` - thêm blink tracking
- [ ] Trả về `is_blinking` trong result

### Phase 2: Head Pose (Cần thiết cho BORED)

- [ ] Sửa `posture_analyzer.py` - export head_pitch, head_roll, head_yaw
- [ ] Truyền vào result từ ai_processor

### Phase 3: Advanced State Detector

- [ ] Tạo file `advanced_state_detector.py`
- [ ] Implement 3 methods: detect_boredom, detect_dazed, detect_distracted

### Phase 4: Integration

- [ ] Thêm vào main.py
- [ ] Update process_frame()
- [ ] Update draw_overlay()

---

## 🎯 KẾT QUẢ MONG ĐỢI

| Trạng thái     | Độ chính xác | Metrics chính                    |
| -------------- | ------------ | -------------------------------- |
| **Focused**    | ~85%         | All metrics good                 |
| **Distracted** | ~80%         | Gaze lệch, head quay             |
| **Bored**      | ~70%         | Neutral + distracted + head tilt |
| **Dazed**      | ~65%         | Mắt mở to + không chớp           |

---

## ⚠️ LƯU Ý

1. **Độ chính xác không cao 100%** - cần thu thập data và fine-tune thresholds
2. **Cần calibration** - mỗi người có baseline khác nhau
3. **Combine với context** - ví dụ: thời gian học, độ khó bài học
4. **False positives** - có thể phát hiện nhầm, cần logic debouncing

---

**Chúc bạn code thành công! 🎭**
