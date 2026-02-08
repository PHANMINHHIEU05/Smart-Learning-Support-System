# 📚 GIAI ĐOẠN 1 - HƯỚNG DẪN CẢI TIẾN GIÁM SÁT

## Tổng quan

Bổ sung 3 tính năng giám sát quan trọng để nâng cao chất lượng phát hiện và bảo vệ sức khỏe người học:

1. **Face Distance Monitoring** - Giám sát khoảng cách mắt-màn hình
2. **Micro-Sleep Detection** - Phát hiện ngủ gật
3. **Study Break Timer** - Timer nghỉ giải lao thông minh

---

## 1️⃣ FACE DISTANCE MONITORING

### 🎯 Mục đích

- Bảo vệ thị lực: Cảnh báo khi ngồi quá gần màn hình
- Phát hiện tư thế xấu: Ngồi quá xa có thể do gù lưng
- Cải thiện ergonomics

### ✅ CODE ĐÃ CÓ SẴN!

**File**: `ai_models/posture_analyzer.py` (dòng 355-373)

Method `calculate_face_distance()` đã implement sẵn:

```python
def calculate_face_distance(self, face_landmarks) -> float:
    """Ước tính khoảng cách mặt-camera qua IPD

    Returns:
        float: IPD normalized (0.05-0.3)
        - > 0.2: Ngồi quá gần
        - 0.1-0.2: Bình thường
        - < 0.1: Ngồi quá xa
    """
```

### 📐 Nguyên lý đã có

**IPD-based Distance** (Inter-Pupillary Distance):

```
IPD_pixel = sqrt((left_eye.x - right_eye.x)² + (left_eye.y - right_eye.y)²)

Normalized IPD (0.05 - 0.3):
- > 0.2: Quá GẦN camera (< 40cm)
- 0.1-0.2: Khoảng cách TỐT (40-80cm)
- < 0.1: Quá XA camera (> 80cm)
```

Nguyên lý: IPD càng LỚN trong frame → càng GẦN camera

### 🔧 Implementation Steps (SỬ DỤNG CODE CÓ SẴN)

#### Bước 1: Gọi method trong ai_processor.py

**File**: `core/ai_processor.py`

**Trong method `_process_frame()`, sau phần posture analysis:**

```python
# Posture analysis - truyền cả face_landmarks
if pose_results.pose_landmarks:
    head_tilt, shoulder_angle, posture_score, is_bad_posture = \
        self.posture_analyzer.process(pose_results.pose_landmarks, face_landmarks)

# >>> THÊM MỚI: Tính face distance <<<
face_distance_ipd = 0.15  # default
if face_landmarks is not None:
    face_distance_ipd = self.posture_analyzer.calculate_face_distance(face_landmarks)

# Lấy posture details
posture_details = self.posture_analyzer.get_posture_details()
```

**Thêm vào return dict:**

```python
return {
    'timestamp': time.time(),
    ...existing fields...,
    'face_distance_ipd': round(face_distance_ipd, 3),  # ← THÊM MỚI
    'posture_details': posture_details,
    'frame': frame
}
```

#### Bước 2: Xử lý distance logic trong main.py

**File**: `main.py`

**Trong `process_frame()`, sau advanced state detection:**

```python
# === FACE DISTANCE MONITORING ===
face_distance_ipd = ai_result.get('face_distance_ipd', 0.15)

# Xác định trạng thái
if face_distance_ipd > 0.2:
    distance_status = 'too_close'
    is_too_close = True
    is_too_far = False
elif face_distance_ipd < 0.1:
    distance_status = 'too_far'
    is_too_close = False
    is_too_far = True
else:
    distance_status = 'good'
    is_too_close = False
    is_too_far = False

# Ước tính khoảng cách thực (cm) - công thức đơn giản hóa
# IPD 0.2 ≈ 35cm, IPD 0.15 ≈ 50cm, IPD 0.1 ≈ 75cm
estimated_distance_cm = int(50 / (face_distance_ipd / 0.15))
```

**Thêm vào return dict:**

```python
return {
    ...existing...,
    'face_distance_ipd': face_distance_ipd,
    'distance_status': distance_status,
    'estimated_distance_cm': estimated_distance_cm,
    'is_too_close': is_too_close,
    'is_too_far': is_too_far
}
```

#### Bước 3: Hiển thị trên UI

**Trong `draw_overlay()`:**

**A. Thêm vào info display:**

```python
# Advanced states
advanced_states = data.get('advanced_states', {})
dominant_state = advanced_states.get('dominant_state', 'normal')
blink_rate = advanced_states.get('blink_rate', 0.0)

# >>> THÊM: Distance info <<<
distance_cm = data.get('estimated_distance_cm', 0)
distance_status = data.get('distance_status', 'unknown')

# Màu theo status
if distance_status == 'too_close':
    dist_color = (0, 0, 255)  # Đỏ
elif distance_status == 'too_far':
    dist_color = (255, 165, 0)  # Cam
else:
    dist_color = (0, 255, 0)  # Xanh

info = [
    f"Focus: {focus_score:.1f} {emoji}",
    f"Drowsy: {'YES!' if data.get('is_drowsy') else 'NO'} (EAR: {data.get('ear_avg', 0):.3f})",
    f"Posture: {data.get('posture_score', 0):.1f} {'(BAD!)' if data.get('is_bad_posture') else '(Good)'}",
    f"Gaze: {data.get('gaze_direction', 'CENTER')} {'(Distracted!)' if data.get('is_distracted') else ''}",
    f"Emotion: {data.get('emotion', 'neutral')} ({data.get('emotion_confidence', 0):.0f}%)",
    f"Blink Rate: {blink_rate:.1f} blinks/min",
    f"State: {dominant_state.upper()}"
]

# Vẽ info với màu tương ứng
for i, text in enumerate(info):
    text_color = color if i == 0 else (255, 255, 255)
    if i == 6 and dominant_state != 'normal':
        text_color = (0, 0, 255)
    cv2.putText(frame, text, (20, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, text_color, 2)
    y += 26

# >>> THÊM: Distance display riêng với màu <<<
cv2.putText(frame, f"Distance: ~{distance_cm}cm",
           (20, y),
           cv2.FONT_HERSHEY_SIMPLEX, 0.55, dist_color, 2)
```

**B. Warning ở giữa màn hình (ưu tiên cao):**

```python
# Cảnh báo ưu tiên cao nhất: Advanced states > Distance > Drowsy > Bad posture
advanced_states = data.get('advanced_states', {})
warning_msg = advanced_states.get('warning_message', '')

if warning_msg:  # Bored, Dazed, Severely Distracted
    cv2.putText(frame, warning_msg, (w//2 - 200, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
elif data.get('is_too_close'):  # ← THÊM: Distance warning
    cv2.putText(frame, "⚠️ TOO CLOSE TO SCREEN!", (w//2 - 180, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
elif data.get('is_too_far'):
    cv2.putText(frame, "⚠️ TOO FAR FROM CAMERA!", (w//2 - 180, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 165, 0), 3)
elif data.get('is_drowsy'):
    cv2.putText(frame, "DROWSY WARNING!", (w//2 - 120, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
elif data.get('is_bad_posture'):
    cv2.putText(frame, "BAD POSTURE!", (w//2 - 100, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
```

### 🧪 Testing

**Test thresholds:**

1. **Ngồi gần camera (30-35cm)** → IPD > 0.2 → "TOO CLOSE"
2. **Ngồi vị trí tốt (50-60cm)** → IPD 0.1-0.2 → "Distance: ~50cm" (xanh)
3. **Ngồi xa (80cm+)** → IPD < 0.1 → "TOO FAR"

**Điều chỉnh thresholds nếu cần:**

```python
# Trong main.py process_frame()
if face_distance_ipd > 0.22:  # Nghiêm ngặt hơn (0.2 → 0.22)
    distance_status = 'too_close'
elif face_distance_ipd < 0.08:  # Lỏng hơn (0.1 → 0.08)
    distance_status = 'too_far'
```

### 📝 Notes

**ƯU ĐIỂM của phương pháp này:**

- ✅ **Không cần code mới** - tận dụng code có sẵn
- ✅ **Nhanh** - chỉ 1 phép tính khoảng cách
- ✅ **Không ảnh hưởng FPS** - O(1) complexity
- ✅ **Đủ chính xác** cho mục đích cảnh báo

**HẠN CHẾ:**

- ❌ Không có calibration - thresholds cố định
- ❌ Ước tính khoảng cách (cm) không chính xác 100%
- ❌ Phụ thuộc góc nhìn camera

**NÂNG CAO (nếu muốn chính xác hơn):**

- Thêm calibration: user ngồi 50cm, lưu baseline_ipd
- Tính focal_length thực tế cho từng webcam
- Sử dụng công thức: `distance_cm = (63mm × focal) / ipd_pixel`

---

## 2️⃣ MICRO-SLEEP DETECTION

### 🎯 Mục đích

- Phát hiện **ngủ gật** (micro-sleep): mắt nhắm 3-10 giây
- Khác với drowsiness: drowsiness = mệt, micro-sleep = thực sự ngủ
- Cực kỳ nguy hiểm khi lái xe, học tập kém hiệu quả

### 🧠 Nguyên lý hoạt động

**Dấu hiệu Micro-Sleep:**

1. **EAR < 0.18** liên tục 3-10 giây (KHÔNG phải nhắm/mở nhắm/mở)
2. **Đầu từ từ cúi xuống** (head_pitch tăng dần)
3. **Blink count = 0** trong khoảng thời gian đó
4. **Không có chuyển động đầu** (head_yaw, head_roll ổn định)

**Phân biệt với Drowsiness:**

```
┌─────────────────────┬──────────────┬──────────────┐
│                     │ Drowsiness   │ Micro-Sleep  │
├─────────────────────┼──────────────┼──────────────┤
│ EAR Duration        │ 1-3s (20-60f)│ 3-10s (90-300f)│
│ Head Movement       │ Có (lắc đầu) │ Không (đứng yên)│
│ Recovery            │ Tự hồi phục  │ CẦN ĐÁNH THỨC │
│ Severity            │ Medium       │ CRITICAL      │
└─────────────────────┴──────────────┴──────────────┘
```

### 🔧 Implementation Steps

#### Bước 1: Mở rộng `DrowsinessDetector`

**File**: `ai_models/drowsiness_detector.py`

**Thêm thuộc tính:**

```python
# Micro-sleep detection (nghiêm trọng hơn drowsiness)
self.microsleep_threshold_frames = 90  # 3 giây @ 30fps
self.microsleep_max_frames = 300       # 10 giây
self.microsleep_counter = 0
self.is_microsleep = False

# Tracking head stability
self.last_head_pitch = 0.0
self.head_pitch_history = []  # Lưu 30 frames gần nhất
self.head_movement_threshold = 5.0  # Độ (ít chuyển động)
```

**Thêm method:**

```python
def detect_microsleep(self,
                     ear_avg: float,
                     head_pitch: float,
                     head_yaw: float,
                     head_roll: float) -> Tuple[bool, int]:
    """
    Phát hiện micro-sleep qua:
    1. EAR thấp kéo dài (3-10s)
    2. Đầu cúi dần
    3. Không có chuyển độn"g đầu
"
    Returns:
        (is_microsleep, microsleep_duration_frames)
    """

    # Điều kiện 1: EAR thấp liên tục
    eyes_closed = ear_avg < 0.18

    # Điều kiện 2: Đầu ổn định (không lắc đầu)
    self.head_pitch_history.append(head_pitch)
    if len(self.head_pitch_history) > 30:
        self.head_pitch_history.pop(0)

    head_movement = 0.0
    if len(self.head_pitch_history) >= 10:
        # Tính độ biến thiên
        head_movement = max(self.head_pitch_history) - min(self.head_pitch_history)

    is_head_stable = head_movement < self.head_movement_threshold

    # Điều kiện 3: Đầu cúi xuống (head_pitch > 15)
    is_head_drooping = head_pitch > 15

    # Kết hợp
    if eyes_closed and is_head_stable and is_head_drooping:
        self.microsleep_counter += 1
    else:
        # Nhanh chóng reset nếu mở mắt
        self.microsleep_counter = 0
        self.is_microsleep = False
        return False, 0

    # Phát hiện micro-sleep
    if self.microsleep_counter >= self.microsleep_threshold_frames:
        self.is_microsleep = True
        return True, self.microsleep_counter

    return False, 0
```

#### Bước 2: Tích hợp vào main.py

**Trong `process_frame()`:**

```python
# Sau khi có posture_details
is_microsleep, microsleep_duration = self.ai_thread.drowsiness_detector.detect_microsleep(
    ear_avg=ear_avg,
    head_pitch=head_pitch,
    head_yaw=head_yaw,
    head_roll=head_roll
)

# Thêm vào return
return {
    ...existing...,
    'is_microsleep': is_microsleep,
    'microsleep_duration': microsleep_duration
}
```

**Trong `draw_overlay()` - CẢNH BÁO ƯU TIÊN CAO NHẤT:**

```python
# Micro-sleep > tất cả warnings khác
if data.get('is_microsleep'):
    # Cảnh báo đỏ nhấp nháy
    if int(time.time() * 2) % 2 == 0:  # Blink effect
        cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 10)
        cv2.putText(frame, "!!! MICRO-SLEEP DETECTED !!!",
                   (w//2 - 200, h//2),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)

        duration_sec = data.get('microsleep_duration', 0) / 30
        cv2.putText(frame, f"Duration: {duration_sec:.1f}s",
                   (w//2 - 100, h//2 + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
```

#### Bước 3: Alert System (Tùy chọn)

**Phát âm thanh cảnh báo:**

```python
# Import thêm
import subprocess  # hoặc pygame.mixer

def play_alert_sound(self):
    """Phát âm thanh beep cảnh báo"""
    # Linux: paplay
    subprocess.Popen(['paplay', '/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga'])

    # Hoặc: Text-to-speech
    subprocess.Popen(['espeak', 'Wake up!'])
```

### 🧪 Testing

1. **Nhắm mắt 1-2 giây** → Chỉ drowsy, KHÔNG micro-sleep
2. **Nhắm mắt 4 giây + cúi đầu** → Nên phát hiện MICRO-SLEEP
3. **Nhắm mắt nhưng lắc đầu** → KHÔNG phải micro-sleep (còn tỉnh)

### 📝 Notes

- **CRITICAL ALERT**: Micro-sleep cần cảnh báo mạnh (âm thanh + nhấp nháy)
- **Độ nhạy**: Có thể điều chỉnh `microsleep_threshold_frames` (90-120)
- **Head drooping**: Dấu hiệu quan trọng để phân biệt với chớp mắt lâu

---

## 3️⃣ STUDY BREAK TIMER

### 🎯 Mục đích

- **Pomodoro technique**: 25 phút học → 5 phút nghỉ
- Ngăn học quá sức: Cảnh báo sau 50 phút liên tục
- Đề xuất bài tập mắt, vai gáy khi nghỉ

### ⏱️ Nguyên lý hoạt động

**Pomodoro Cycle:**

```
┌──────────────────────────────────────────┐
│  FOCUS (25 min)  →  BREAK (5 min)       │
│        ↓                   ↓              │
│  Tập trung học     Nghỉ ngơi, bài tập    │
└──────────────────────────────────────────┘

Sau 4 Pomodoro → Long Break (15-30 min)
```

**Smart Break Suggestions:**

- Nếu `is_drowsy` hoặc `is_dazed` → Đề xuất nghỉ sớm
- Nếu `is_bad_posture` nhiều → Đề xuất bài tập vai gáy
- Nếu `blink_rate` thấp → Đề xuất bài tập mắt

### 🔧 Implementation Steps

#### Bước 1: Tạo `StudyBreakTimer` class

**File**: `ai_models/study_break_timer.py`

**Thuộc tính:**

```python
# Pomodoro settings
self.focus_duration = 25 * 60      # 25 phút = 1500 giây
self.short_break_duration = 5 * 60  # 5 phút
self.long_break_duration = 15 * 60  # 15 phút
self.pomodoro_count = 0             # Đếm số Pomodoro hoàn thành

# Timer state
self.mode = 'FOCUS'  # 'FOCUS', 'SHORT_BREAK', 'LONG_BREAK'
self.start_time = time.time()
self.elapsed_time = 0
self.remaining_time = self.focus_duration

# Warning thresholds
self.continuous_study_warning = 50 * 60  # 50 phút
self.has_warned = False

# Tracking
self.total_study_time = 0
self.total_break_time = 0
```

**Methods:**

```python
def start_focus_session(self):
    """Bắt đầu phiên học 25 phút"""
    self.mode = 'FOCUS'
    self.start_time = time.time()
    self.remaining_time = self.focus_duration
    self.has_warned = False
    print("🎯 Focus session started! (25 min)")

def start_break(self, break_type='SHORT'):
    """Bắt đầu nghỉ giải lao"""
    self.mode = f'{break_type}_BREAK'
    self.start_time = time.time()

    if break_type == 'SHORT':
        self.remaining_time = self.short_break_duration
        print("☕ Short break! (5 min)")
    else:
        self.remaining_time = self.long_break_duration
        print("🌴 Long break! (15 min)")

def update(self) -> dict:
    """
    Update mỗi frame

    Returns:
        {
            'mode': 'FOCUS' | 'SHORT_BREAK' | 'LONG_BREAK',
            'elapsed': int (seconds),
            'remaining': int (seconds),
            'progress': float (0-1),
            'should_break': bool,
            'break_suggestion': str
        }
    """
    current_time = time.time()
    self.elapsed_time = int(current_time - self.start_time)
    self.remaining_time = max(0,
        (self.focus_duration if self.mode == 'FOCUS' else
         self.short_break_duration if 'SHORT' in self.mode else
         self.long_break_duration) - self.elapsed_time
    )

    # Progress bar
    total_duration = (self.focus_duration if self.mode == 'FOCUS' else
                     self.short_break_duration if 'SHORT' in self.mode else
                     self.long_break_duration)
    progress = self.elapsed_time / total_duration

    # Check if session ended
    should_break = False
    if self.remaining_time == 0:
        if self.mode == 'FOCUS':
            should_break = True
            self.pomodoro_count += 1
        else:
            # Break ended → auto start focus
            self.start_focus_session()

    # Warning continuous study
    if self.mode == 'FOCUS' and self.elapsed_time > 3000 and not self.has_warned:
        # > 50 min continuous study
        self.has_warned = True
        print("⚠️ WARNING: You've been studying for over 50 minutes!")

    return {
        'mode': self.mode,
        'elapsed': self.elapsed_time,
        'remaining': self.remaining_time,
        'progress': min(1.0, progress),
        'should_break': should_break,
        'pomodoro_count': self.pomodoro_count
    }

def suggest_break_activity(self,
                          is_drowsy: bool,
                          is_bad_posture: bool,
                          blink_rate: float) -> str:
    """
    Đề xuất hoạt động nghỉ ngơi dựa trên tình trạng
    """
    suggestions = []

    if is_drowsy:
        suggestions.append("💤 Đứng dậy đi lại 2 phút")
        suggestions.append("💧 Uống nước lạnh")

    if is_bad_posture:
        suggestions.append("🤸 Xoay vai 10 lần")
        suggestions.append("🧘 Duỗi lưng, ngả người ra sau")

    if blink_rate < 12:
        suggestions.append("👁️ Bài tập mắt: Nhìn xa 20s")
        suggestions.append("👁️ Nhắm mắt nghỉ 30s")

    if not suggestions:
        suggestions = [
            "☕ Uống nước",
            "🚶 Đi lại vài phút",
            "🪟 Nhìn ra ngoài cửa sổ"
        ]

    return suggestions[0]  # Trả về đề xuất quan trọng nhất
```

#### Bước 2: Tích hợp vào main.py

**Trong `__init__`:**

```python
from ai_models.study_break_timer import StudyBreakTimer

self.break_timer = StudyBreakTimer()
self.break_timer.start_focus_session()  # Auto-start
```

**Trong `process_frame()`:**

```python
# Update timer
timer_info = self.break_timer.update()

# Kiểm tra nếu cần nghỉ
if timer_info['should_break']:
    # Phát âm thanh hoặc notification
    print(f"\n{'='*50}")
    print("⏰ TIME'S UP! Take a break!")
    print(f"{'='*50}\n")

    # Đề xuất activity
    suggestion = self.break_timer.suggest_break_activity(
        is_drowsy=data.get('is_drowsy', False),
        is_bad_posture=data.get('is_bad_posture', False),
        blink_rate=advanced_states.get('blink_rate', 15)
    )
    print(f"💡 Suggestion: {suggestion}\n")

    # Start break
    if self.break_timer.pomodoro_count % 4 == 0:
        self.break_timer.start_break('LONG')
    else:
        self.break_timer.start_break('SHORT')

# Thêm vào return
return {
    ...existing...,
    'timer_info': timer_info
}
```

**Trong `draw_overlay()` - Timer Display:**

```python
# Timer info (góc phải dưới)
timer_info = data.get('timer_info', {})
mode = timer_info.get('mode', 'FOCUS')
remaining = timer_info.get('remaining', 0)
progress = timer_info.get('progress', 0.0)

# Format time
mins = remaining // 60
secs = remaining % 60

# Màu theo mode
if 'BREAK' in mode:
    timer_color = (0, 255, 0)  # Xanh
else:
    timer_color = (255, 200, 0)  # Vàng

# Display timer
timer_text = f"{mode}: {mins:02d}:{secs:02d}"
cv2.putText(frame, timer_text,
           (w - 220, h - 60),
           cv2.FONT_HERSHEY_SIMPLEX, 0.7, timer_color, 2)

# Progress bar
bar_width = 200
bar_height = 15
bar_x = w - 220
bar_y = h - 40

# Background
cv2.rectangle(frame, (bar_x, bar_y),
             (bar_x + bar_width, bar_y + bar_height),
             (50, 50, 50), -1)

# Progress fill
fill_width = int(bar_width * progress)
cv2.rectangle(frame, (bar_x, bar_y),
             (bar_x + fill_width, bar_y + bar_height),
             timer_color, -1)

# Border
cv2.rectangle(frame, (bar_x, bar_y),
             (bar_x + bar_width, bar_y + bar_height),
             (255, 255, 255), 1)

# Pomodoro count
pomodoro_count = timer_info.get('pomodoro_count', 0)
cv2.putText(frame, f"🍅 x{pomodoro_count}",
           (w - 220, h - 10),
           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 100), 2)
```

**Thêm phím tắt:**

```python
elif key == ord('b'):
    # Manual break
    self.break_timer.start_break('SHORT')
elif key == ord('p'):
    # Pause/Resume timer
    # TODO: Implement pause functionality
    pass
```

#### Bước 3: Notification System (Tùy chọn)

**Linux Desktop Notification:**

```python
import subprocess

def show_notification(title: str, message: str):
    """Hiện notification popup"""
    subprocess.Popen([
        'notify-send',
        title,
        message,
        '-u', 'critical',  # Urgency
        '-t', '10000'      # 10 seconds
    ])

# Sử dụng
if timer_info['should_break']:
    show_notification(
        "⏰ Study Break Time!",
        "You've completed a Pomodoro! Take a 5-minute break."
    )
```

### 🧪 Testing

1. **Đặt focus_duration = 60s** (test nhanh)
2. **Chờ 60 giây** → Nên có thông báo "TIME'S UP"
3. **Kiểm tra progress bar** → Nên chạy từ 0% → 100%
4. **Kiểm tra break suggestions** → Thử với is_drowsy=True

### 📝 Notes

- **Customizable**: User có thể tự đặt 25/5, 50/10, 90/20...
- **Smart pause**: Nên tự động pause khi không detect face (user rời khỏi)
- **Persistence**: Lưu pomodoro_count vào file để track theo ngày

---

## 🚀 TỔNG KẾT IMPLEMENTATION

### Thứ tự thực hiện đề xuất:

1. **Face Distance** (dễ nhất) - 30-45 phút
2. **Study Break Timer** (hữu ích nhất) - 1 giờ
3. **Micro-Sleep** (quan trọng nhất) - 45 phút

### Files cần tạo:

```
ai_models/
├── face_distance_monitor.py      (NEW)
├── study_break_timer.py           (NEW)
└── drowsiness_detector.py         (MODIFY - thêm micro-sleep)
```

### Files cần sửa:

```
main.py                            (MODIFY - tích hợp 3 features)
core/ai_processor.py               (MODIFY - pass head angles)
```

### Testing Checklist:

- [ ] Face distance: 30cm, 50cm, 80cm → correct warnings
- [ ] Micro-sleep: nhắm mắt 4s + cúi đầu → detected
- [ ] Break timer: countdown works, notifications work
- [ ] Integration: tất cả features hoạt động đồng thời
- [ ] FPS: vẫn giữ ~15 FPS

### Expected Outcome:

```
┌──────────────────────────────────────────────┐
│ Focus: 78.5 🎯                              │
│ Drowsy: NO (EAR: 0.285)                     │
│ Posture: 72.0 (Good)                        │
│ Gaze: CENTER                                │
│ Emotion: neutral (85%)                      │
│ Blink Rate: 14.2 blinks/min                 │
│ State: NORMAL                               │
│ Distance: 52cm (good) ← NEW                 │
│                                              │
│            FOCUS: 23:45 ← NEW               │
│            [████████░░] 95%                 │
│            🍅 x3                             │
└──────────────────────────────────────────────┘
```

---

## 💡 TIPS & BEST PRACTICES

### Performance:

- ✅ Face distance: O(1) - chỉ tính khoảng cách 2 điểm
- ✅ Micro-sleep: O(1) - chỉ so sánh thresholds
- ✅ Break timer: O(1) - chỉ time.time()
- 👉 **KHÔNG ẢNH HƯỞNG FPS**

### User Experience:

- 🔔 Notifications quan trọng nhưng không spam
- 🎨 Visual feedback rõ ràng, dễ hiểu
- ⚙️ Cho phép customize (thresholds, durations)
- 💾 Lưu settings vào config file

### Error Handling:

- Face not detected → return default values
- Calibration failed → use fallback constants
- Timer overflow → auto-reset

---

## 📚 RESOURCES

### Thư viện có thể dùng:

- **Notification**: `notify-send` (Linux), `win10toast` (Windows)
- **Sound**: `pygame.mixer`, `playsound`, `paplay`
- **Config**: `json`, `configparser`, `pydantic`

### References:

- IPD measurement: https://en.wikipedia.org/wiki/Pupillary_distance
- Micro-sleep research: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2656292/
- Pomodoro technique: https://francescocirillo.com/pages/pomodoro-technique

---

**Chúc bạn implement thành công! 🚀**

Nếu gặp vấn đề gì, hãy hỏi cụ thể từng phần nhé!
