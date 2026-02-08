Tôi đang làm đồ án "Smart Study Behavior Analytics" - Hệ thống phân tích hành vi học tập thông minh.

## THÔNG TIN DỰ ÁN:

- Python 3.10, OpenCV, MediaPipe, DeepFace
- Sử dụng Z-score adaptive detection (không dùng hard-coded thresholds)
- Multi-threading: Camera Thread + AI Processor Thread
- SQLite database lưu dữ liệu cho Big Data analysis

## CẤU TRÚC DỰ ÁN:

pythonProject/
├── ai_models/
│ ├── adaptive_detector.py ✅ Z-score detection
│ ├── calibrator.py ✅ 10s calibration
│ ├── drowsiness_detector.py ✅ EAR calculation
│ ├── focus_calculator.py ✅ Focus score
│ ├── gaze_tracker.py 🔄 ĐANG LÀM
│ ├── moving_average_filter.py ✅ EMA filter
│ ├── posture_analyzer.py ✅ Head tilt, pitch, IPD
│ └── user_profile.py ✅ Save/Load profile
├── core/
│ ├── ai_processor.py ✅ Face Mesh + Pose
│ └── camera_thread.py ✅ Camera capture
├── database/
│ ├── db_manager.py ✅ SQLite manager
│ └── models.py ✅ SQL schema
├── config/
├── data/
├── utils/
└── requirements.txt

## ĐÃ HOÀN THÀNH (Step 1-8):

1. ✅ Project structure
2. ✅ Virtual environment + dependencies
3. ✅ Database schema (SQLite)
4. ✅ Camera Thread
5. ✅ AI Processor (Face Mesh + Pose)
6. ✅ Calibrator (10s baseline collection)
7. ✅ Moving Average Filter (EMA)
8. ✅ Head Pitch + Face Distance (IPD)

## ĐANG LÀM - STEP 9: GAZE TRACKER

File: ai_models/gaze_tracker.py

- Theo dõi hướng nhìn từ Iris landmarks (468, 473)
- Tính gaze_ratio = vị trí iris trong mắt
- Phát hiện nhìn LEFT/RIGHT/CENTER
- Tính distraction_score

## CÒN LẠI:

- Step 10: Emotion Analyzer (DeepFace)
- Step 11: Phone Usage Detector
- Step 12: Focus Score Calculator v2
- Step 13: Main Integration

## YÊU CẦU:

- Hướng dẫn từng bước, KHÔNG tự code
- Giải thích chi tiết để tôi hiểu và tự viết
- Kiểm tra code sau khi tôi viết xong

Hãy đọc file gaze_tracker.py hiện tại và hướng dẫn tôi tiếp tục.
