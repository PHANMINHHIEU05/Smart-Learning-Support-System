"""
Test Adaptive Detector với Moving Average Filter
"""

import cv2
import time
from queue import Queue, Empty
from core.camera_thread import CameraThread
from core.ai_processor import AIProcessorThread
from ai_models.user_profile import UserProfile
from ai_models.adaptive_detector import AdaptiveDetector

print("="*60)
print("TEST ADAPTIVE DETECTOR")
print("="*60)

# Load user profile từ calibration
profile = UserProfile.load_from_file("data/user_profile.json")

if profile is None or not profile.is_calibrated:
    print("❌ Chưa có profile! Hãy chạy test_calibration.py trước.")
    exit(1)

print(f"\n📊 Loaded Profile:")
print(f"   EAR Mean: {profile.ear_data.mean:.4f}, Std: {profile.ear_data.std:.4f}")
print(f"   Head Tilt Mean: {profile.head_tilt_data.mean:.2f}")

# Khởi tạo queues
frame_queue = Queue(maxsize=2)
result_queue = Queue(maxsize=10)

# Khởi tạo threads
camera_thread = CameraThread(camera_index=0, frame_queue=frame_queue)
ai_thread = AIProcessorThread(frame_queue=frame_queue, result_queue=result_queue)

# Khởi tạo Adaptive Detector
detector = AdaptiveDetector(
    user_profile=profile,
    z_threshold_drowsy=-2.0,
    z_threshold_posture=2.0,
    consecutive_frames=15,
    filter_window=7
)

# Start threads
camera_thread.start()
ai_thread.start()

print("\n⏳ Đợi khởi động...")
time.sleep(3)

print("\n📺 Đang giám sát với Adaptive Detection")
print("   - Thử nhắm mắt 1-2 giây để test DROWSY")
print("   - Thử nghiêng đầu để test BAD POSTURE")
print("   - Nhấn 'q' để thoát")
print("="*60)

try:
    while True:
        try:
            result = result_queue.get(timeout=0.1)
            
            frame = result['frame']
            
            # Xử lý qua Adaptive Detector
            detection = detector.process(
                ear_avg=result['ear_avg'],
                head_tilt=result['head_tilt'],
                shoulder_angle=result['shoulder_angle']
            )
            
            # Vẽ thông tin lên frame
            y_pos = 30
            
            # Raw vs Smoothed EAR
            cv2.putText(frame, f"Raw EAR: {detection.raw_ear:.3f} | Smoothed: {detection.smoothed_ear:.3f}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_pos += 30
            
            # Z-scores
            z_color = (0, 255, 0) if detection.z_ear > -1.5 else (0, 165, 255) if detection.z_ear > -2 else (0, 0, 255)
            cv2.putText(frame, f"Z-Score EAR: {detection.z_ear:.2f}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, z_color, 2)
            y_pos += 35
            
            # Drowsy warning
            if detection.is_drowsy:
                cv2.putText(frame, "!!! BUON NGU !!!", 
                           (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            elif detection.drowsy_frames > 0:
                cv2.putText(frame, f"Drowsy counter: {detection.drowsy_frames}/{detector.consecutive_frames}", 
                           (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            else:
                cv2.putText(frame, "Tinh tao", 
                           (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_pos += 35
            
            # Posture
            posture_color = (0, 255, 0) if not detection.is_bad_posture else (0, 0, 255)
            posture_text = "TU THE XAU!" if detection.is_bad_posture else "Tu the tot"
            cv2.putText(frame, f"Z-Head: {detection.z_head_tilt:.2f} | Z-Shoulder: {detection.z_shoulder:.2f}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, posture_color, 2)
            y_pos += 30
            cv2.putText(frame, posture_text, 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, posture_color, 2)
            
            # Hiển thị frame
            cv2.imshow('Adaptive Detector Test', frame)
            
        except Empty:
            pass
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\n⚠️ Nhận Ctrl+C")

finally:
    camera_thread.stop()
    ai_thread.stop()
    camera_thread.join(timeout=2)
    ai_thread.join(timeout=2)
    cv2.destroyAllWindows()
    
    print("\n" + "="*60)
    print("✅ TEST HOÀN TẤT!")
    print("="*60)