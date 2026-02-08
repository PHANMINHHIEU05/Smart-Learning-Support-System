# 🚀 HƯỚNG DẪN TỐI ƯU HIỆU NĂNG (FPS 9 → 20+)

## 📊 ĐÁNH GIÁ HIỆN TẠI

**FPS hiện tại: 9** → ❌ **QUÁ THẤP**

| Mức FPS | Đánh giá    | Trải nghiệm     |
| ------- | ----------- | --------------- |
| < 10    | ❌ Rất lag  | Không dùng được |
| 10-15   | ⚠️ Còn lag  | Chấp nhận được  |
| 15-20   | ✅ Tạm ổn   | Khá mượt        |
| 20-30   | ✅ Tốt      | Rất mượt        |
| > 30    | ✅ Xuất sắc | Hoàn hảo        |

---

## 🔍 PHÂN TÍCH NGUYÊN NHÂN FPS THẤP

### 1. **Phone Detector (YOLOv8) - Thủ phạm chính** 🔴

- **Load:** ~60-70% CPU mỗi lần chạy
- **Tần suất:** Mỗi 5 frames
- **Thời gian:** ~100-150ms mỗi inference

### 2. **Emotion Analyzer (DeepFace)** 🟡

- **Load:** ~30-40% CPU
- **Tần suất:** Mỗi 15 frames
- **Thời gian:** ~80-120ms

### 3. **Face Mesh + Pose (MediaPipe)** 🟢

- **Load:** ~20% CPU
- **Tần suất:** Mỗi frame
- **Thời gian:** ~20-30ms

---

## 🛠️ GIẢI PHÁP TỐI ƯU - ƯU TIÊN CAO → THẤP

### ✅ **CẤP ĐỘ 1: TẮT/GIẢM PHONE DETECTOR (Tăng ~3-5 FPS)**

**Vị trí:** `main.py` - dòng ~30

**OPTION 1: Giảm tần suất check (Khuyến nghị)**

```python
# Thay đổi từ:
self.PHONE_CHECK_INTERVAL = 5

# Thành:
self.PHONE_CHECK_INTERVAL = 10  # Check mỗi 10 frames thay vì 5
# Hoặc
self.PHONE_CHECK_INTERVAL = 15  # Càng cao càng nhanh, nhưng phản hồi chậm hơn
```

**OPTION 2: Tắt hoàn toàn (Nếu không cần)**

```python
# Thay đổi từ:
self.PHONE_CHECK_INTERVAL = 5

# Thành:
self.PHONE_CHECK_INTERVAL = 999999  # Gần như tắt
```

**Hiệu quả:** +3-5 FPS → **FPS mới: ~12-14**

---

### ✅ **CẤP ĐỘ 2: GIẢM EMOTION ANALYZER (Tăng ~2-3 FPS)**

**Vị trí:** `main.py` - dòng ~31

**OPTION 1: Giảm tần suất**

```python
# Thay đổi từ:
self.EMOTION_CHECK_INTERVAL = 15

# Thành:
self.EMOTION_CHECK_INTERVAL = 30  # Check mỗi 30 frames (1 giây)
# Hoặc
self.EMOTION_CHECK_INTERVAL = 60  # Check mỗi 2 giây
```

**OPTION 2: Resize frame nhỏ hơn**

```python
# Trong process_frame(), thay đổi:
small_frame = cv2.resize(frame, (320, 240))

# Thành:
small_frame = cv2.resize(frame, (224, 224))  # Nhỏ hơn = nhanh hơn
# Hoặc
small_frame = cv2.resize(frame, (160, 160))  # Rất nhỏ - cực nhanh nhưng kém chính xác
```

**Hiệu quả:** +2-3 FPS → **FPS mới: ~14-17**

---

### ✅ **CẤP ĐỘ 3: TỐI ƯU MEDIAPIPE (Tăng ~1-2 FPS)**

#### 3.1. Tắt Face Mesh refinement

**Vị trí:** `core/ai_processor.py` - trong `_init_models()`

```python
# Thay đổi từ:
self.face_mesh = self.mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,  # ← Tắt cái này
    ...
)

# Thành:
self.face_mesh = self.mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=False,  # Tắt iris detection - nhanh hơn
    ...
)
```

**⚠️ LƯU Ý:** Nếu tắt `refine_landmarks=False`, **GazeTracker sẽ KHÔNG hoạt động** (vì không có iris landmarks). Chỉ làm nếu bạn không cần gaze tracking!

#### 3.2. Giảm resolution xử lý

**Vị trí:** `core/ai_processor.py` - trong `_process_frame()`

```python
# Thay đổi từ:
scale = 320 / max(h, w)

# Thành:
scale = 240 / max(h, w)  # Nhỏ hơn = nhanh hơn
# Hoặc
scale = 192 / max(h, w)  # Cực nhỏ - cực nhanh
```

**Hiệu quả:** +1-2 FPS → **FPS mới: ~15-19**

---

### ✅ **CẤP ĐỘ 4: SKIP FRAMES (Tăng ~2-4 FPS)**

**Ý tưởng:** AI Processor không xử lý MỌI frame, mà skip 1 vài frame

**Vị trí:** `core/ai_processor.py` - trong `run()`

**Thêm code sau:**

```python
def run(self):
    if not self._init_models():
        return

    self.running = True
    self.start_time = time.time()
    print("✅ AI Processor Thread đã khởi động")

    # THÊM MỚI: Skip frame counter
    frame_skip_count = 0
    SKIP_INTERVAL = 1  # Skip 1 frame, process 1 frame

    while self.running:
        try:
            frame = self.frame_queue.get(timeout=1)

            # THÊM MỚI: Skip logic
            frame_skip_count += 1
            if frame_skip_count <= SKIP_INTERVAL:
                continue  # Skip frame này
            frame_skip_count = 0  # Reset

            result = self._process_frame(frame)
            # ... phần còn lại giữ nguyên
```

**Giải thích:**

- `SKIP_INTERVAL = 1`: Skip 1, process 1 → FPS tăng ~2x
- `SKIP_INTERVAL = 2`: Skip 2, process 1 → FPS tăng ~3x (nhưng lag hơn)

**Hiệu quả:** +2-4 FPS → **FPS mới: ~17-23**

---

### ✅ **CẤP ĐỘ 5: GIẢM CAMERA FPS (Tăng ~1-2 FPS)**

**Vị trí:** `core/camera_thread.py` - trong `_init_camera()`

```python
# Thay đổi từ:
self.cap.set(cv2.CAP_PROP_FPS, 30)

# Thành:
self.cap.set(cv2.CAP_PROP_FPS, 20)  # 20 FPS đủ cho AI
# Hoặc
self.cap.set(cv2.CAP_PROP_FPS, 15)  # 15 FPS - cực kỳ nhẹ
```

**Hiệu quả:** +1-2 FPS

---

## 📋 CHECKLIST TỐI ƯU - THEO THỨ TỰ

### Bước 1: TẮT/GIẢM Phone Detector (BẮT BUỘC)

- [ ] Tăng `PHONE_CHECK_INTERVAL` từ 5 → 10 hoặc 15
- [ ] Hoặc tắt hoàn toàn nếu không cần

### Bước 2: Giảm Emotion Analyzer

- [ ] Tăng `EMOTION_CHECK_INTERVAL` từ 15 → 30
- [ ] Resize emotion frame xuống 224x224

### Bước 3: Tối ưu MediaPipe (Optional)

- [ ] Giảm AI processing resolution xuống 240 hoặc 192
- [ ] Tắt `refine_landmarks` (nếu không cần gaze)

### Bước 4: Skip Frames (Nếu vẫn chưa đủ)

- [ ] Thêm skip logic với `SKIP_INTERVAL = 1`

### Bước 5: Giảm Camera FPS (Cuối cùng)

- [ ] Giảm từ 30 → 20 FPS

---

## 🎯 DỰ ĐOÁN KẾT QUẢ

| Tối ưu                 | FPS dự kiến | Độ khó          |
| ---------------------- | ----------- | --------------- |
| **Chỉ làm Bước 1**     | ~12-14      | ⭐ Dễ           |
| **Bước 1 + 2**         | ~14-17      | ⭐⭐ Dễ         |
| **Bước 1 + 2 + 3**     | ~15-19      | ⭐⭐ Trung bình |
| **Bước 1 + 2 + 3 + 4** | ~17-23      | ⭐⭐⭐ Khó      |
| **Làm tất cả**         | ~20-25      | ⭐⭐⭐ Khó      |

---

## ⚠️ TRADE-OFFS CẦN BIẾT

| Tối ưu                | Tăng FPS | Mất tính năng             |
| --------------------- | -------- | ------------------------- |
| Giảm Phone Interval   | ++       | Phản hồi phone chậm hơn   |
| Giảm Emotion Interval | ++       | Cập nhật emotion chậm hơn |
| Tắt refine_landmarks  | +        | **Mất Gaze Tracking**     |
| Skip frames           | +++      | Có thể giật hình          |
| Giảm Camera FPS       | +        | Video ít mượt hơn         |

---

## 🧪 TEST & DEBUG

### Kiểm tra FPS sau mỗi thay đổi:

1. Thay đổi 1 cái
2. Chạy app
3. Quan sát FPS trên góc phải màn hình
4. Nếu đủ 15+ FPS → DỪNG
5. Nếu chưa → Tiếp tục bước tiếp theo

### Debug nếu FPS vẫn thấp:

```bash
# Check CPU usage
htop

# Check nếu có process khác đang chạy
ps aux | grep python
```

---

**Khuyến nghị:** Làm **Bước 1 + Bước 2** trước, kiểm tra FPS. Nếu đạt 15-17 FPS → **DỪNG LẠI**, không cần tối ưu thêm!

**Chúc bạn tối ưu thành công! 🚀**
