# Smart Learning Support System - Camera Monitoring

## 📍 Location

```
/home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend/src/features/monitoring/
```

## ✅ System Status

- **Camera**: /dev/video0 @ 640x480 ✅
- **OpenCV**: 4.13.0 ✅
- **MediaPipe**: 0.10.32 ✅
- **Manual Exposure**: ENABLED (brightness optimized)
- **Emotion Detection**: DISABLED (performance mode)

## 🚀 Quick Start

### Cách 1: Script tự động (Recommended)

```bash
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend/src/features/monitoring
./run.sh
```

### Cách 2: Manual

```bash
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend/src/features/monitoring
source venv/bin/activate
python main.py
```

## ⌨️ Controls

- **Q**: Thoát ứng dụng
- **C**: Calibration (giữ tư thế chuẩn 10s)

## 📊 Features

✅ **Gaze Tracking** - Theo dõi hướng nhìn  
✅ **Drowsiness Detection** - Phát hiện buồn ngủ (EAR metric)  
✅ **Posture Analysis** - Phân tích tư thế ngồi  
✅ **Focus Score** - Điểm tập trung tổng hợp  
✅ **Advanced States** - Phát hiện bored/dazed/distracted  
✅ **Microsleep Detection** - Phát hiện ngủ gật  
❌ **Emotion Detection** - Đã tắt để tối ưu performance

## 🎨 Camera Settings

Current configuration (optimized for brightness + FPS):

- **Exposure**: 200 (manual mode)
- **Brightness**: 150
- **Gain**: 50
- **FPS**: ~15 (hardware limit)

Để điều chỉnh:

```bash
python utils/tune_camera_settings.py
```

## 📈 Performance

| Metric        | Target    | Current |
| ------------- | --------- | ------- |
| Camera FPS    | 15+       | ~15 ✅  |
| Display FPS   | 30        | 30 ✅   |
| AI Processing | Real-time | ✅      |

## 🔧 Troubleshooting

### Camera không hoạt động

```bash
# Check device
ls -l /dev/video*

# Test camera
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL'); cap.release()"
```

### Dependencies thiếu

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Hình ảnh quá tối

Edit `config/performance_config.py`:

```python
CAMERA_EXPOSURE_VALUE = 250  # Tăng từ 200
CAMERA_BRIGHTNESS = 170      # Tăng từ 150
```

## 📝 Notes

- App sử dụng threading architecture (Camera Thread + AI Thread + Display Thread)
- Display decoupled from AI processing → mượt mà ngay cả khi AI chậm
- Manual exposure mode giữ FPS cao (~15) thay vì auto mode chỉ được 5 FPS
- Database lưu tại `data/user_profile.json` + SQLite database
