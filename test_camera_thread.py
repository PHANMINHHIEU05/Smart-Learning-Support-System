import cv2 
import time 
from queue import Queue, Empty , Full
from core.camera_thread import CameraThread
print("="*50)
print("TEST CAMERA THREAD")
print("="*50)

frame_queue = Queue(maxsize=2)
camera_thread = CameraThread(camera_index=0, frame_queue=frame_queue)
camera_thread.start()
frame_count = 0
start_time = time.time()
time.sleep(2)  # chờ camera khởi động
try:
     while True:
          if not frame_queue.empty():
               frame = frame_queue.get()
               frame_count += 1
               elapsed = time.time() - start_time
               if elapsed >= 1.0:
                    fps = frame_count / elapsed
                    print(f"FPS: {fps:.2f}")
                    frame_count = 0
                    start_time = time.time()
                    camera_fps = camera_thread.get_fps()
                    print(f"Camera Thread FPS: {camera_fps:.2f}")
               cv2.putText(frame, f"FPS: {fps:.2f}", (10,30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
               cv2.imshow("Camera Frame", frame)
          if cv2.waitKey(1) & 0xFF == ord('q'):
               break
except KeyboardInterrupt:
     print("Dừng test camera thread")
finally:
     camera_thread.stop()
     camera_thread.join(timeout=2)
     cv2.destroyAllWindows()