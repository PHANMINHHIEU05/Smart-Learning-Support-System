# 🎯 HƯỚNG DẪN TỐI ƯU HÓA MODEL PHÁT HIỆN TƯ THẾ & MẤT TẬP TRUNG

## 📊 PHÂN TÍCH HIỆN TẠI

### Các file cần tối ưu:

1. `ai_models/posture_analyzer.py` - Phát hiện tư thế sai
2. `ai_models/gaze_tracker.py` - Phát hiện mất tập trung
3. `ai_models/drowsiness_detector.py` - Phát hiện buồn ngủ
4. `ai_models/focus_calculator.py` - Tính điểm tập trung

---

## 🔧 PHẦN 1: TỐI ƯU POSTURE ANALYZER

### Vấn đề hiện tại:

```
❌ head_tilt chỉ dùng vertical_diff, không tính khoảng cách thực
❌ shoulder_angle threshold quá mềm (< 20° được coi tốt)
❌ Chỉ có 2 thành phần (head + shoulder), thiếu back curve
❌ Không phân biệt: cúi đầu vs gập lưng
❌ posture_frames = 30 quá lâu (1 giây)
```

### ✅ Giải pháp 1.1: Thêm Back Curve Detection

**Vị trí:** Thêm method mới trong class `PostureAnalyzer`

```python
def calculate_back_curve(self, landmarks) -> float:
    """Tính độ cong lưng từ góc giữa vai-hông

    Returns: Góc cong (độ) - Cao = cong lưng xấu
    """
    left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
    right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]

    # Trung điểm vai và hông
    mid_shoulder_x = (left_shoulder.x + right_shoulder.x) / 2
    mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
    mid_hip_x = (left_hip.x + right_hip.x) / 2
    mid_hip_y = (left_hip.y + right_hip.y) / 2

    # Vector từ hông đến vai
    dx = mid_shoulder_x - mid_hip_x
    dy = mid_shoulder_y - mid_hip_y

    # Góc so với vertical (0 = thẳng lưng)
    if dy == 0:
        return 0.0
    back_curve = abs(math.degrees(math.atan(dx / abs(dy))))
    return back_curve
```

**Ngưỡng khuyến nghị:**

- `< 15°`: Tư thế tốt
- `15° - 30°`: Cần điều chỉnh
- `> 30°`: Cong lưng xấu

---

### ✅ Giải pháp 1.2: Cải thiện Posture Score

**Thay đổi:** Sửa method `calculate_posture_score()`

```python
def calculate_posture_score(self, head_tilt: float, shoulder_angle: float,
                           back_curve: float = 0.0) -> float:
    """Tính điểm tư thế tổng hợp (0-100)

    Phân bố điểm:
    - Head tilt: 40 điểm (quan trọng nhất)
    - Back curve: 35 điểm (cong lưng)
    - Shoulder alignment: 25 điểm (vai cân bằng)
    """
    # 1. HEAD TILT (0-40 điểm)
    if head_tilt < 5:
        head_score = 40   # Hoàn hảo
    elif head_tilt < 10:
        head_score = 30   # Tốt
    elif head_tilt < 15:
        head_score = 15   # Chấp nhận
    else:
        head_score = 5    # Xấu - cúi quá

    # 2. BACK CURVE (0-35 điểm)
    if back_curve < 15:
        back_score = 35   # Thẳng lưng
    elif back_curve < 25:
        back_score = 20   # Hơi cong
    else:
        back_score = 5    # Cong nhiều

    # 3. SHOULDER (0-25 điểm)
    if shoulder_angle < 8:
        shoulder_score = 25   # Cân bằng
    elif shoulder_angle < 15:
        shoulder_score = 15   # Lệch nhẹ
    else:
        shoulder_score = 5    # Quay nghiêng

    return head_score + back_score + shoulder_score
```

---

### ✅ Giải pháp 1.3: Điều chỉnh Thresholds

**Thay đổi trong `__init__()`:**

```python
def __init__(self,
             head_tilt_threshold: float = 12.0,    # Giảm từ 15 → 12
             posture_frames: int = 20,              # Giảm từ 30 → 20
             back_curve_threshold: float = 25.0):   # Thêm mới
    self.head_tilt_threshold = head_tilt_threshold
    self.posture_frames = posture_frames
    self.back_curve_threshold = back_curve_threshold
    # ... rest of init
```

---

### ✅ Giải pháp 1.4: Cập nhật process()

**Thay đổi:** Sửa method `process()`

```python
def process(self, pose_landmarks) -> Tuple[float, float, float, bool]:
    if pose_landmarks is None:
        return 0.0, 0.0, 100, False

    landmarks = pose_landmarks.landmark
    head_tilt = self.calculate_head_tilt(landmarks)
    shoulder_angle = self.calculate_shoulder_angle(landmarks)
    back_curve = self.calculate_back_curve(landmarks)  # THÊM MỚI

    posture_score = self.calculate_posture_score(head_tilt, shoulder_angle, back_curve)

    # Điều kiện xấu tư thế: bất kỳ cái nào vượt ngưỡng
    is_bad = (head_tilt > self.head_tilt_threshold or
             back_curve > self.back_curve_threshold or
             shoulder_angle > 20)

    if is_bad:
        self.bad_posture_counter += 1
    else:
        # Hồi phục nhanh khi tư thế tốt
        self.bad_posture_counter = max(0, self.bad_posture_counter - 2)
        self.is_bad_posture = False

    if self.bad_posture_counter >= self.posture_frames:
        self.is_bad_posture = True

    return head_tilt, shoulder_angle, posture_score, self.is_bad_posture
```

---

## 🔧 PHẦN 2: TỐI ƯU GAZE TRACKER

### Vấn đề hiện tại:

```
❌ distraction_frames = 30 quá cứng nhắc
❌ Chỉ xét iris position, bỏ qua eye openness
❌ Không detect nhìn lên/xuống (chỉ có trái/phải)
❌ Counter reset về 0 ngay khi nhìn CENTER (quá khắt khe)
❌ Không có soft scoring (chỉ có TRUE/FALSE)
```

### ✅ Giải pháp 2.1: Thêm Eye Landmarks

**Vị trí:** Thêm constants ở đầu file

```python
# Thêm landmarks cho eye openness
LEFT_EYE_TOP = 386
LEFT_EYE_BOTTOM = 374
RIGHT_EYE_TOP = 159
RIGHT_EYE_BOTTOM = 145
```

---

### ✅ Giải pháp 2.2: Thêm Eye Openness Detection

**Vị trí:** Thêm method mới trong class

```python
def _get_eye_openness(self, landmarks) -> Tuple[float, float]:
    """Tính độ mở mắt (eye aspect ratio)

    Returns: (openness_left, openness_right)
    Giá trị: 0.1-0.4 bình thường, < 0.15 = mắt nhắm
    """
    # Mắt trái
    left_vertical = self._calculate_distance(
        landmarks[LEFT_EYE_TOP],
        landmarks[LEFT_EYE_BOTTOM]
    )
    left_horizontal = self._calculate_distance(
        landmarks[LEFT_EYE_OUTER],
        landmarks[LEFT_EYE_INNER]
    )
    left_openness = left_vertical / left_horizontal if left_horizontal > 0 else 0.5

    # Mắt phải
    right_vertical = self._calculate_distance(
        landmarks[RIGHT_EYE_TOP],
        landmarks[RIGHT_EYE_BOTTOM]
    )
    right_horizontal = self._calculate_distance(
        landmarks[RIGHT_EYE_OUTER],
        landmarks[RIGHT_EYE_INNER]
    )
    right_openness = right_vertical / right_horizontal if right_horizontal > 0 else 0.5

    return left_openness, right_openness
```

---

### ✅ Giải pháp 2.3: Thêm Soft Distraction Tracking

**Thay đổi trong `__init__()`:**

```python
def __init__(self, left_threshold: float = 0.35,
             right_threshold: float = 0.65,
             distraction_frames: int = 25,           # Giảm từ 30 → 25
             eye_closed_threshold: float = 0.15):    # THÊM MỚI
    self.left_threshold = left_threshold
    self.right_threshold = right_threshold
    self.distraction_frames = distraction_frames
    self.eye_closed_threshold = eye_closed_threshold

    # Trạng thái cũ
    self.distraction_counter = 0
    self.is_distracted = False
    self.current_direction = "CENTER"
    self.current_ratio = 0.5

    # THÊM MỚI: Soft tracking
    self.distraction_score = 0.0      # 0.0-1.0, dùng cho focus calculator
    self.eyes_closed_counter = 0
    self.eye_openness = 0.25
```

---

### ✅ Giải pháp 2.4: Cải thiện process()

**Thay đổi:** Sửa method `process()`

```python
def process(self, face_landmarks) -> Tuple[float, str, bool]:
    if face_landmarks is None:
        return 0.5, "CENTER", False

    landmarks = face_landmarks.landmark

    # 1. Tính iris position
    self.current_ratio = self._get_iris_position(landmarks)
    direction = self._determine_direction()

    # 2. Tính eye openness
    left_open, right_open = self._get_eye_openness(landmarks)
    self.eye_openness = (left_open + right_open) / 2.0

    # 3. Check mắt nhắm
    if self.eye_openness < self.eye_closed_threshold:
        self.eyes_closed_counter += 1
    else:
        self.eyes_closed_counter = 0

    eyes_closed = self.eyes_closed_counter > 10  # 10+ frames = mắt nhắm

    # 4. Soft distraction counter
    if direction != "CENTER":
        self.distraction_counter += 1.5   # Tăng nhanh khi lệch
    else:
        # Giảm dần (không reset về 0 ngay)
        self.distraction_counter = max(0, self.distraction_counter - 2)

    # 5. Tính distraction score (0-1) cho focus calculator
    self.distraction_score = min(1.0, self.distraction_counter / 20.0)

    # 6. Final: mất tập trung nếu nhìn lệch lâu HOẶC nhắm mắt
    self.is_distracted = (self.distraction_counter >= self.distraction_frames) or eyes_closed
    self.current_direction = direction

    return self.current_ratio, direction, self.is_distracted
```

---

## 🔧 PHẦN 3: TỐI ƯU DROWSINESS DETECTOR

### Vấn đề hiện tại:

```
❌ ear_threshold = 0.2 có thể không phù hợp mọi người
❌ consec_frames = 20 cố định, không adaptive
❌ Không có blink detection (phân biệt chớp mắt vs ngủ)
```

### ✅ Giải pháp 3.1: Thêm Blink Detection

```python
def __init__(self, ear_threshold: float = 0.21, consec_frames: int = 15):
    self.ear_threshold = ear_threshold
    self.consec_frames = consec_frames
    self.eye_closed_counter = 0
    self.is_drowsy = False

    # THÊM MỚI: Blink tracking
    self.blink_counter = 0
    self.blink_cooldown = 0
    self.total_blinks = 0
    self.is_blinking = False
```

### ✅ Giải pháp 3.2: Phân biệt Blink vs Drowsy

```python
def process(self, face_landmarks) -> Tuple[float, float, bool]:
    if face_landmarks is None:
        return 0.0, 0.0, False

    landmarks = face_landmarks.landmark
    ear_left = self.calculate_ear(landmarks, self.LEFT_EYE)
    ear_right = self.calculate_ear(landmarks, self.RIGHT_EYE)
    ear_avg = (ear_left + ear_right) / 2.0

    # Cooldown từ blink trước
    if self.blink_cooldown > 0:
        self.blink_cooldown -= 1

    if ear_avg < self.ear_threshold:
        self.eye_closed_counter += 1

        # Blink = nhắm mắt ngắn (3-8 frames)
        if 3 <= self.eye_closed_counter <= 8 and self.blink_cooldown == 0:
            self.is_blinking = True
    else:
        # Mắt mở lại
        if self.is_blinking and self.eye_closed_counter <= 8:
            self.total_blinks += 1
            self.blink_cooldown = 10  # Cooldown 10 frames

        self.eye_closed_counter = 0
        self.is_blinking = False
        self.is_drowsy = False

    # Drowsy = nhắm mắt lâu (> consec_frames)
    if self.eye_closed_counter >= self.consec_frames:
        self.is_drowsy = True

    return ear_left, ear_right, self.is_drowsy
```

---

## 🔧 PHẦN 4: TỐI ƯU FOCUS CALCULATOR

### Vấn đề hiện tại:

```
❌ Weights không được balance tốt
❌ Không có penalty cho mắt nhắm
❌ Emotion weight quá cao (15%) cho trường hợp này
```

### ✅ Giải pháp: Điều chỉnh Weights

```python
def __init__(self,
             w_ear: float = 0.20,        # Drowsiness: 20%
             w_posture: float = 0.25,    # Tư thế: 25% (tăng)
             w_emotion: float = 0.10,    # Emotion: 10% (giảm)
             w_gaze: float = 0.25,       # Gaze: 25% (tăng)
             w_phone: float = 0.20):     # Phone: 20%
```

### ✅ Thêm Distraction Score vào Focus

```python
def calculate_focus_score(self,
                          ear_avg: float,
                          posture_score: float,
                          emotion: str = 'neutral',
                          gaze_ratio: float = 0.5,
                          is_distracted: bool = False,
                          is_using_phone: bool = False,
                          distraction_score: float = 0.0) -> float:  # THÊM MỚI
    """
    distraction_score: 0.0-1.0, soft measure từ GazeTracker
    """
    # ... existing code ...

    # Thêm penalty từ distraction_score
    gaze_penalty = distraction_score * 30  # Max -30 điểm

    focus = (
        self.w_ear * self.last_ear_score +
        self.w_posture * self.last_posture_score +
        self.w_emotion * self.last_emotion_score +
        self.w_gaze * (self.last_gaze_score - gaze_penalty) +  # Apply penalty
        self.w_phone * self.last_phone_score
    )

    return round(max(0, min(100, focus)), 1)
```

---

## 📋 PHẦN 5: CHECKLIST THỰC HIỆN

### Bước 1: Sửa `posture_analyzer.py`

- [ ] Thêm `back_curve_threshold` vào `__init__()`
- [ ] Thêm method `calculate_back_curve()`
- [ ] Sửa `calculate_posture_score()` với 3 thành phần
- [ ] Sửa `process()` để dùng back_curve
- [ ] Giảm `posture_frames` từ 30 → 20

### Bước 2: Sửa `gaze_tracker.py`

- [ ] Thêm eye landmarks constants
- [ ] Thêm `eye_closed_threshold` vào `__init__()`
- [ ] Thêm biến `distraction_score`, `eyes_closed_counter`
- [ ] Thêm method `_get_eye_openness()`
- [ ] Sửa `process()` với soft tracking
- [ ] Giảm `distraction_frames` từ 30 → 25

### Bước 3: Sửa `drowsiness_detector.py`

- [ ] Thêm blink tracking variables
- [ ] Sửa `process()` phân biệt blink vs drowsy
- [ ] Giảm `consec_frames` từ 20 → 15

### Bước 4: Sửa `focus_calculator.py`

- [ ] Điều chỉnh weights
- [ ] Thêm parameter `distraction_score`
- [ ] Apply gaze penalty

### Bước 5: Sửa `main.py`

- [ ] Truyền `distraction_score` từ GazeTracker vào FocusCalculator

---

## 🧪 PHẦN 6: KIỂM TRA SAU KHI SỬA

### Test Cases:

1. **Tư thế tốt**: Ngồi thẳng, nhìn màn hình
   - Expected: `posture_score >= 80`, `focus >= 75`

2. **Cúi đầu**: Cúi nhìn bàn phím
   - Expected: `head_tilt > 12`, `posture_score < 50`

3. **Cong lưng**: Gập người về phía trước
   - Expected: `back_curve > 25`, `is_bad_posture = True`

4. **Nhìn sang bên 2 giây**: Quay đầu nhìn bên cạnh
   - Expected: `direction = LEFT/RIGHT`, `is_distracted = True`

5. **Nhắm mắt 1 giây**: Nhắm mắt lâu
   - Expected: `is_drowsy = True`

6. **Chớp mắt**: Chớp mắt bình thường
   - Expected: `is_drowsy = False`, `blink detected`

7. **Dùng điện thoại**: Giơ phone lên
   - Expected: `is_using_phone = True`, `focus < 50`

---

## 📊 BẢNG THAM KHẢO THRESHOLDS

| Metric         | Giá trị tốt | Cảnh báo                 | Xấu                |
| -------------- | ----------- | ------------------------ | ------------------ |
| Head Tilt      | < 10°       | 10-15°                   | > 15°              |
| Back Curve     | < 15°       | 15-25°                   | > 25°              |
| Shoulder Angle | < 8°        | 8-15°                    | > 15°              |
| Gaze Ratio     | 0.35-0.65   | 0.25-0.35 hoặc 0.65-0.75 | < 0.25 hoặc > 0.75 |
| EAR (Eye)      | > 0.25      | 0.2-0.25                 | < 0.2              |
| Eye Openness   | > 0.2       | 0.15-0.2                 | < 0.15             |

---

## 🎓 TIPS BỔ SUNG

### 1. Calibration per-user

```python
# Trong main.py, thêm calibration:
def calibrate(self):
    # Thu thập 100 frames khi user ngồi đúng tư thế
    # Lấy trung bình làm baseline
    # Điều chỉnh thresholds dựa trên baseline
```

### 2. Smoothing với Moving Average

```python
# Dùng EMA filter cho các metrics
from ai_models.moving_average_filter import MovingAverageFilter

self.ear_filter = MovingAverageFilter(window_size=5)
ear_avg_smooth = self.ear_filter.update(ear_avg)
```

### 3. Debug Mode

```python
# Thêm debug output
if self.debug:
    print(f"Head: {head_tilt:.1f}° | Back: {back_curve:.1f}° | Gaze: {direction}")
```

---

**Chúc bạn code thành công! 🚀**
