# 🎯 HƯỚNG DẪN PHÁT HIỆN TƯ THẾ SAI VỚI WEBCAM

## ⚠️ GIỚI HẠN CỦA WEBCAM

Webcam thông thường chỉ quay được **phần thân trên**:

- ✅ Có thể thấy: **Mặt, Cổ, Vai, một phần cánh tay**
- ❌ Không thể thấy: **Hông, Lưng, Chân**

Do đó, **KHÔNG THỂ** dùng:

- `LEFT_HIP`, `RIGHT_HIP` landmarks
- Back curve detection (cần thấy hông)

---

## 📊 CÁC METRICS CÓ THỂ DÙNG VỚI WEBCAM

### Từ Face Mesh (478 landmarks):

| Metric            | Mô tả              | Cách tính                      |
| ----------------- | ------------------ | ------------------------------ |
| **Head Pitch**    | Cúi/Ngẩng đầu      | Góc giữa forehead-nose-chin    |
| **Head Yaw**      | Quay trái/phải     | Tỷ lệ khoảng cách má trái/phải |
| **Head Roll**     | Nghiêng đầu        | Góc đường nối 2 mắt            |
| **Face Distance** | Khoảng cách camera | Khoảng cách giữa 2 mắt (IPD)   |

### Từ Pose (phần trên):

| Metric                     | Mô tả        | Cách tính                               |
| -------------------------- | ------------ | --------------------------------------- |
| **Shoulder Alignment**     | Vai cân bằng | Góc nghiêng đường nối 2 vai             |
| **Head-Shoulder Distance** | Cổ cúi       | Khoảng cách mũi đến trung điểm vai      |
| **Shoulder Visibility**    | Vai có hiện  | Visibility score của shoulder landmarks |

---

## 🔧 PHẦN 1: PHÁT HIỆN TƯ THẾ XẤU BẰNG FACE MESH

### ✅ Giải pháp 1.1: Head Pitch (Cúi/Ngẩng đầu)

**Nguyên lý:** Khi cúi đầu, chin (cằm) gần mũi hơn, forehead (trán) xa hơn.

```python
# Landmarks cần dùng
FOREHEAD = 10
NOSE_TIP = 1
CHIN = 152

def calculate_head_pitch(self, face_landmarks) -> float:
    """Tính góc cúi đầu từ Face Mesh

    Returns:
        float: Góc pitch (độ)
        - Dương (+) = Cúi đầu xuống
        - Âm (-) = Ngẩng đầu lên
        - 0 = Nhìn thẳng
    """
    forehead = face_landmarks.landmark[10]  # FOREHEAD
    nose = face_landmarks.landmark[1]       # NOSE_TIP
    chin = face_landmarks.landmark[152]     # CHIN

    # Khoảng cách từ forehead đến nose vs nose đến chin
    upper = math.sqrt((forehead.x - nose.x)**2 + (forehead.y - nose.y)**2)
    lower = math.sqrt((nose.x - chin.x)**2 + (nose.y - chin.y)**2)

    # Tỷ lệ - nếu upper > lower = cúi đầu
    if lower == 0:
        return 0.0

    ratio = upper / lower

    # Convert sang góc (calibrated values)
    # ratio = 1.0 -> 0°, ratio = 1.3 -> ~15° cúi, ratio = 0.7 -> ~15° ngẩng
    pitch_angle = (ratio - 1.0) * 50  # Scale factor

    return pitch_angle
```

**Ngưỡng khuyến nghị:**

- `|pitch| < 10°`: Tốt
- `10° < |pitch| < 20°`: Cảnh báo
- `|pitch| > 20°`: Cúi/Ngẩng quá nhiều

---

### ✅ Giải pháp 1.2: Head Yaw (Quay trái/phải)

**Nguyên lý:** Khi quay đầu sang trái, má phải gần camera hơn (lớn hơn), má trái xa hơn (nhỏ hơn).

```python
# Landmarks
LEFT_CHEEK = 234
RIGHT_CHEEK = 454
NOSE_TIP = 1

def calculate_head_yaw(self, face_landmarks) -> float:
    """Tính góc quay đầu trái/phải

    Returns:
        float: Góc yaw (độ)
        - Dương (+) = Quay sang phải
        - Âm (-) = Quay sang trái
        - 0 = Nhìn thẳng
    """
    left_cheek = face_landmarks.landmark[234]
    right_cheek = face_landmarks.landmark[454]
    nose = face_landmarks.landmark[1]

    # Khoảng cách từ mũi đến má trái vs má phải
    dist_left = abs(nose.x - left_cheek.x)
    dist_right = abs(nose.x - right_cheek.x)

    # Tỷ lệ
    if dist_left + dist_right == 0:
        return 0.0

    # Normalize về -1 đến 1
    yaw_ratio = (dist_right - dist_left) / (dist_right + dist_left)

    # Convert sang góc (-45° đến +45°)
    yaw_angle = yaw_ratio * 45

    return yaw_angle
```

**Ngưỡng khuyến nghị:**

- `|yaw| < 15°`: Tốt (nhìn thẳng)
- `15° < |yaw| < 30°`: Quay nhẹ
- `|yaw| > 30°`: Quay nhiều (mất tập trung)

---

### ✅ Giải pháp 1.3: Head Roll (Nghiêng đầu)

**Nguyên lý:** Đường nối 2 mắt nên nằm ngang. Nếu nghiêng = tư thế xấu.

```python
# Landmarks
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263

def calculate_head_roll(self, face_landmarks) -> float:
    """Tính góc nghiêng đầu

    Returns:
        float: Góc roll (độ)
        - Dương = Nghiêng sang phải
        - Âm = Nghiêng sang trái
    """
    left_eye = face_landmarks.landmark[33]
    right_eye = face_landmarks.landmark[263]

    dx = right_eye.x - left_eye.x
    dy = right_eye.y - left_eye.y

    # Góc so với đường ngang
    roll_angle = math.degrees(math.atan2(dy, dx))

    return roll_angle
```

**Ngưỡng khuyến nghị:**

- `|roll| < 5°`: Tốt
- `5° < |roll| < 15°`: Nghiêng nhẹ
- `|roll| > 15°`: Nghiêng nhiều

---

### ✅ Giải pháp 1.4: Face Distance (Khoảng cách camera)

**Nguyên lý:** IPD (Inter-Pupillary Distance) - khoảng cách giữa 2 mắt. Ngồi càng gần camera thì IPD càng lớn.

```python
def calculate_face_distance(self, face_landmarks) -> float:
    """Ước tính khoảng cách mặt-camera

    Returns:
        float: IPD normalized (0.05-0.3)
        - > 0.2: Ngồi quá gần
        - 0.1-0.2: Bình thường
        - < 0.1: Ngồi quá xa
    """
    left_eye = face_landmarks.landmark[33]   # LEFT_EYE_OUTER
    right_eye = face_landmarks.landmark[263] # RIGHT_EYE_OUTER

    ipd = math.sqrt(
        (left_eye.x - right_eye.x) ** 2 +
        (left_eye.y - right_eye.y) ** 2
    )

    return ipd
```

**Ngưỡng khuyến nghị:**

- `0.10 < IPD < 0.18`: Khoảng cách tốt
- `IPD > 0.20`: Quá gần màn hình
- `IPD < 0.08`: Quá xa màn hình

---

## 🔧 PHẦN 2: PHÁT HIỆN TƯ THẾ XẤU BẰNG POSE

### ✅ Giải pháp 2.1: Shoulder Alignment (Vai cân bằng)

**Đây là metric đã có trong code hiện tại** - giữ nguyên.

```python
def calculate_shoulder_angle(self, landmarks) -> float:
    """Tính góc nghiêng vai"""
    left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]

    dx = right_shoulder.x - left_shoulder.x
    dy = right_shoulder.y - left_shoulder.y

    if dx == 0:
        return 0.0
    return abs(math.degrees(math.atan(dy / dx)))
```

---

### ✅ Giải pháp 2.2: Head-Shoulder Distance (Cổ cúi - THAY THẾ BACK CURVE)

**Nguyên lý:** Khi cúi người về phía trước, khoảng cách từ mũi đến vai **GIẢM** (mũi đi xuống gần vai hơn theo trục Y). Đây là cách thay thế back curve mà không cần thấy hông!

```python
def calculate_neck_posture(self, pose_landmarks) -> float:
    """Tính tư thế cổ/vai - thay thế back curve

    Returns:
        float: Neck score (0-100)
        - 100 = Cổ thẳng, đầu cao
        - 50 = Cúi nhẹ
        - 0 = Cúi nhiều, đầu gần vai
    """
    landmarks = pose_landmarks.landmark

    nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
    left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]

    # Trung điểm vai
    mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2

    # Khoảng cách từ mũi đến vai (theo trục Y)
    # Y trong MediaPipe: 0 = trên, 1 = dưới
    # Nên nose.y < mid_shoulder_y = đầu cao hơn vai (tốt)
    vertical_distance = mid_shoulder_y - nose.y

    # Normalize:
    # - vertical_distance > 0.15: Rất tốt (đầu cao)
    # - vertical_distance ~ 0.10: Bình thường
    # - vertical_distance < 0.05: Cúi nhiều

    if vertical_distance > 0.20:
        return 100.0  # Excellent
    elif vertical_distance > 0.15:
        return 85.0   # Good
    elif vertical_distance > 0.10:
        return 65.0   # OK
    elif vertical_distance > 0.05:
        return 40.0   # Cúi nhẹ
    else:
        return 15.0   # Cúi nhiều - xấu
```

---

### ✅ Giải pháp 2.3: Shoulder Visibility Check

**Nguyên lý:** Nếu không thấy vai = có thể đang ngồi nghiêng hoặc quay lưng.

```python
def check_shoulder_visibility(self, pose_landmarks) -> bool:
    """Kiểm tra có thấy cả 2 vai không

    Returns:
        bool: True nếu thấy cả 2 vai rõ
    """
    landmarks = pose_landmarks.landmark

    left_vis = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].visibility
    right_vis = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].visibility

    # Cả 2 vai cần visibility > 0.5
    return left_vis > 0.5 and right_vis > 0.5
```

---

## 🔧 PHẦN 3: TÍCH HỢP VÀO POSTURE_ANALYZER.PY

### Cập nhật class PostureAnalyzer:

```python
class PostureAnalyzer:
    """Phân tích tư thế cho WEBCAM (chỉ thấy phần trên)"""

    def __init__(self,
                 head_tilt_threshold: float = 12.0,
                 posture_frames: int = 20,
                 neck_threshold: float = 50.0):  # Thay back_curve
        """
        Args:
            head_tilt_threshold: Góc cúi đầu tối đa
            posture_frames: Frames liên tục xấu tư thế
            neck_threshold: Điểm neck posture tối thiểu (0-100)
        """
        self.head_tilt_threshold = head_tilt_threshold
        self.posture_frames = posture_frames
        self.neck_threshold = neck_threshold

        self.bad_posture_counter = 0
        self.is_bad_posture = False
        self.mp_pose = mp.solutions.pose
```

### Cập nhật calculate_posture_score():

```python
def calculate_posture_score(self, head_tilt: float, shoulder_angle: float,
                           neck_score: float = 75.0,
                           head_pitch: float = 0.0,
                           head_roll: float = 0.0) -> float:
    """Tính điểm tư thế cho webcam (0-100)

    Phân bố điểm:
    - Neck posture: 30 điểm (thay back curve)
    - Head tilt (từ pose): 25 điểm
    - Head pitch (từ face): 20 điểm
    - Shoulder alignment: 15 điểm
    - Head roll: 10 điểm
    """
    # 1. NECK POSTURE (0-30)
    neck_points = min(30, neck_score * 0.30)

    # 2. HEAD TILT from Pose (0-25)
    if head_tilt < 5:
        head_tilt_points = 25
    elif head_tilt < 10:
        head_tilt_points = 18
    elif head_tilt < 15:
        head_tilt_points = 10
    else:
        head_tilt_points = 3

    # 3. HEAD PITCH from Face (0-20)
    abs_pitch = abs(head_pitch)
    if abs_pitch < 10:
        pitch_points = 20
    elif abs_pitch < 20:
        pitch_points = 12
    else:
        pitch_points = 4

    # 4. SHOULDER ALIGNMENT (0-15)
    if shoulder_angle < 5:
        shoulder_points = 15
    elif shoulder_angle < 12:
        shoulder_points = 10
    else:
        shoulder_points = 3

    # 5. HEAD ROLL (0-10)
    abs_roll = abs(head_roll)
    if abs_roll < 5:
        roll_points = 10
    elif abs_roll < 12:
        roll_points = 6
    else:
        roll_points = 2

    total = neck_points + head_tilt_points + pitch_points + shoulder_points + roll_points
    return min(100.0, max(0.0, total))
```

### Cập nhật process():

```python
def process(self, pose_landmarks, face_landmarks=None) -> Tuple[float, float, float, bool]:
    """Xử lý và trả về kết quả phân tích tư thế

    Args:
        pose_landmarks: MediaPipe Pose landmarks
        face_landmarks: MediaPipe Face Mesh landmarks (optional)

    Returns:
        (head_tilt, shoulder_angle, posture_score, is_bad_posture)
    """
    if pose_landmarks is None:
        return 0.0, 0.0, 100.0, False

    landmarks = pose_landmarks.landmark

    # 1. Từ Pose
    head_tilt = self.calculate_head_tilt(landmarks)
    shoulder_angle = self.calculate_shoulder_angle(landmarks)
    neck_score = self.calculate_neck_posture(pose_landmarks)

    # 2. Từ Face Mesh (nếu có)
    head_pitch = 0.0
    head_roll = 0.0
    if face_landmarks is not None:
        head_pitch = self.calculate_head_pitch(face_landmarks)
        head_roll = self.calculate_head_roll(face_landmarks)

    # 3. Tính tổng điểm
    posture_score = self.calculate_posture_score(
        head_tilt, shoulder_angle, neck_score, head_pitch, head_roll
    )

    # 4. Tracking bad posture
    is_bad = (posture_score < 50 or
             neck_score < self.neck_threshold or
             head_tilt > self.head_tilt_threshold)

    if is_bad:
        self.bad_posture_counter += 1
    else:
        self.bad_posture_counter = max(0, self.bad_posture_counter - 2)
        self.is_bad_posture = False

    if self.bad_posture_counter >= self.posture_frames:
        self.is_bad_posture = True

    return head_tilt, shoulder_angle, posture_score, self.is_bad_posture
```

---

## 📋 CHECKLIST THỰC HIỆN

### Bước 1: Thêm methods mới vào `posture_analyzer.py`

- [ ] Thêm `calculate_head_pitch(face_landmarks)`
- [ ] Thêm `calculate_head_yaw(face_landmarks)` (optional, cho gaze)
- [ ] Thêm `calculate_head_roll(face_landmarks)`
- [ ] Thêm `calculate_neck_posture(pose_landmarks)` ← THAY CHO BACK CURVE
- [ ] Thêm `check_shoulder_visibility(pose_landmarks)` (optional)

### Bước 2: Sửa `__init__()`

- [ ] Thêm `neck_threshold` parameter
- [ ] Giảm `posture_frames` từ 30 → 20

### Bước 3: Sửa `calculate_posture_score()`

- [ ] Thêm parameters: `neck_score`, `head_pitch`, `head_roll`
- [ ] Cập nhật công thức tính điểm 5 thành phần

### Bước 4: Sửa `process()`

- [ ] Thêm parameter `face_landmarks`
- [ ] Gọi các methods mới
- [ ] Cập nhật logic bad posture detection

### Bước 5: Sửa `ai_processor.py`

- [ ] Truyền `face_landmarks` vào `posture_analyzer.process()`

---

## 🧪 TEST CASES

| Test | Hành động                        | Expected                                   |
| ---- | -------------------------------- | ------------------------------------------ |
| 1    | Ngồi thẳng, nhìn thẳng           | `posture_score >= 80`                      |
| 2    | Cúi đầu xuống                    | `head_pitch > 15`, `score < 60`            |
| 3    | Quay đầu sang bên                | `head_yaw > 20`, detected                  |
| 4    | Nghiêng đầu                      | `head_roll > 10`, detected                 |
| 5    | Cúi người về trước (vai gần mặt) | `neck_score < 50`, `is_bad_posture = True` |
| 6    | Ngồi quá gần camera              | `face_distance > 0.2`, warning             |

---

## 📊 BẢNG THRESHOLDS CHO WEBCAM

| Metric              | Rất tốt   | Tốt       | Cảnh báo  | Xấu                |
| ------------------- | --------- | --------- | --------- | ------------------ |
| Head Pitch          | < 5°      | 5-10°     | 10-20°    | > 20°              |
| Head Yaw            | < 10°     | 10-20°    | 20-30°    | > 30°              |
| Head Roll           | < 3°      | 3-8°      | 8-15°     | > 15°              |
| Shoulder Angle      | < 3°      | 3-8°      | 8-15°     | > 15°              |
| Neck Score          | > 85      | 65-85     | 40-65     | < 40               |
| Face Distance (IPD) | 0.12-0.16 | 0.10-0.18 | 0.08-0.20 | < 0.08 hoặc > 0.22 |

---

## 💡 TIPS

### 1. Calibration cá nhân

```python
# Khi bắt đầu, yêu cầu user ngồi đúng tư thế 5 giây
# Thu thập baseline cho từng metric
# Điều chỉnh threshold dựa trên baseline
```

### 2. Kết hợp multiple metrics

```python
# Đừng chỉ dựa vào 1 metric
# Ví dụ: head_pitch cao + neck_score thấp = chắc chắn cúi
```

### 3. Smoothing

```python
# Dùng moving average để tránh jitter
from ai_models.moving_average_filter import MovingAverageFilter
self.neck_filter = MovingAverageFilter(window_size=5)
```

---

**Chúc bạn code thành công! 🚀**
