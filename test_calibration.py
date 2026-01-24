"""
Test Calibration Module
"""

import cv2
import time
from queue import Queue, Empty
from core.camera_thread import CameraThread
from core.ai_processor import AIProcessorThread
from ai_models.calibrator import Calibrator
from ai_models.user_profile import UserProfile

print("="*60)
print("TEST CALIBRATION MODULE")
print("="*60)

# Khởi tạo queues
frame_queue = Queue(maxsize=2)
result_queue = Queue(maxsize=10)

# Khởi tạo threads
camera_thread = CameraThread(camera_index=0, frame_queue=frame_queue)
ai_thread = AIProcessorThread(frame_queue=frame_queue, result_queue=result_queue)

# Khởi tạo calibrator (10 giây)
calibrator = Calibrator(duration=10.0)

# Start threads
camera_thread.start()
ai_thread.start()

print("\n⏳ Đợi khởi động...")
time.sleep(3)

# Bắt đầu calibration
print("\n" + "="*60)
calibrator.start()

user_profile = None

try:
    while True:
        # Lấy kết quả từ AI Thread
        try:
            result = result_queue.get(timeout=0.1)
            
            frame = result['frame']
            
            # Nếu đang calibrating, thêm dữ liệu
            if calibrator.is_calibrating:
                calibrator.add_sample(
                    ear_avg=result['ear_avg'],
                    head_tilt=result['head_tilt'],
                    shoulder_angle=result['shoulder_angle'],
                    distance=50.0  # Tạm thời dùng giá trị cố định
                )
                
                # Vẽ progress bar lên frame
                progress_text = calibrator.get_progress_bar(20)
                cv2.putText(frame, f"CALIBRATING: {progress_text}", 
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
                # Kiểm tra hoàn thành
                if calibrator.is_complete():
                    user_profile = calibrator.finish()
                    
                    if user_profile:
                        # Lưu profile
                        user_profile.save_to_file("data/user_profile.json")
                        print(user_profile)
                    
                    break
            
            # Hiển thị frame
            cv2.imshow('Calibration', frame)
            
        except Empty:
            pass  # Không có frame, tiếp tục vòng lặp
        
        # Nhấn 'q' để hủy (PHẢI Ở NGOÀI try-except)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n⚠️ Calibration bị hủy!")
            break

except KeyboardInterrupt:
    print("\n⚠️ Nhận Ctrl+C")

finally:
    # Cleanup
    camera_thread.stop()
    ai_thread.stop()
    camera_thread.join(timeout=2)
    ai_thread.join(timeout=2)
    cv2.destroyAllWindows()
    
    print("\n" + "="*60)
    print("✅ TEST HOÀN TẤT!")
    
    # Test load profile
    if user_profile:
        print("\n📂 Test load profile từ file...")
        loaded_profile = UserProfile.load_from_file("data/user_profile.json")
        if loaded_profile:
            print(f"   EAR Mean: {loaded_profile.ear_data.mean:.4f}")
            print(f"   Is Calibrated: {loaded_profile.is_calibrated}")
    
    print("="*60)