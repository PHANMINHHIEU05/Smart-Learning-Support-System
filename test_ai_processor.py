"""
Test AI Processor Thread với Camera Thread
"""

import cv2
from queue import Queue
from core.camera_thread import CameraThread
from core.ai_processor import AIProcessorThread
import time

print("="*60)
print("TEST AI PROCESSOR + CAMERA THREAD")
print("="*60)

# Tạo queues
frame_queue = Queue(maxsize=2)
result_queue = Queue(maxsize=10)

# Khởi động Camera Thread
camera_thread = CameraThread(camera_index=0, frame_queue=frame_queue)
camera_thread.start()

# Khởi động AI Processor Thread
ai_thread = AIProcessorThread(frame_queue=frame_queue, result_queue=result_queue)
ai_thread.start()

print("\n⏳ Đợi threads khởi động...")
time.sleep(3)

print("\n📺 Hiển thị kết quả AI")
print("   Nhấn 'q' để thoát")
print("="*60)

try:
    while True:
        # Lấy kết quả từ AI Thread
        if not result_queue.empty():
            result = result_queue.get()
            
            frame = result['frame']
            
            # Vẽ thông tin lên frame
            y_pos = 30
            
            # FPS
            cv2.putText(frame, f"Camera: {camera_thread.get_fps():.1f} FPS | AI: {ai_thread.get_fps():.1f} FPS", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_pos += 35
            
            # EAR
            ear_color = (0, 255, 0) if not result['is_drowsy'] else (0, 0, 255)
            cv2.putText(frame, f"EAR: {result['ear_avg']:.3f} {'DROWSY!' if result['is_drowsy'] else 'OK'}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, ear_color, 2)
            y_pos += 35
            
            # Posture
            posture_color = (0, 255, 0) if not result['is_bad_posture'] else (0, 0, 255)
            cv2.putText(frame, f"Posture: {result['posture_score']:.0f}/100 {'' if not result['is_bad_posture'] else 'BAD!'}", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, posture_color, 2)
            y_pos += 35
            
            # Focus Score
            focus_score = result['focus_score']
            if focus_score >= 80:
                focus_color = (0, 255, 0)
            elif focus_score >= 60:
                focus_color = (0, 255, 255)
            else:
                focus_color = (0, 0, 255)
            
            cv2.putText(frame, f"FOCUS: {focus_score:.0f}/100", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 1.2, focus_color, 3)
            
            # Hiển thị
            cv2.imshow('AI Processor Test', frame)
            
            # In ra console mỗi 30 frame
            if result_queue.qsize() % 30 == 0:
                print(f"Focus: {focus_score:.0f} | EAR: {result['ear_avg']:.3f} | Posture: {result['posture_score']:.0f}")
        
        # Thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\n⚠️ Nhận Ctrl+C")

finally:
    # Dừng threads
    print("\n🛑 Đang dừng threads...")
    camera_thread.stop()
    ai_thread.stop()
    
    camera_thread.join(timeout=3)
    ai_thread.join(timeout=3)
    
    cv2.destroyAllWindows()
    
    print("\n" + "="*60)
    print("✅ TEST HOÀN TẤT!")
    print("="*60)