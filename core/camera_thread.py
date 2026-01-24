import cv2 
import threading
import time
from queue import Queue, Full , Empty

class CameraThread(threading.Thread):
     """tạo 1 thread chuyên đọc từ camera
     Attributes:
     camera_index (int): Index của camera (0, 1, 2...)
     frame_queue (Queue): Queue để gửi frame đến AI Thread
     running (bool): Cờ điều khiển vòng lặp
     fps (float): Frame per second hiện tại 
     """
     def __init__(self, camera_index: int = 0, frame_queue: int = None):
          # khởi tạo thread
          super().__init__()
          self.daemon = True # đặt daemon để thread tự động dừng khi main thread kết thúc
          self.camera_index = camera_index
          self.cap = None
          if frame_queue is None:
               self.frame_queue = Queue(maxsize=2)  # hàng đợi chứa frame
          else:
               self.frame_queue = frame_queue
          self.running = False
          self.fps = 0.0
          self.frame_count = 0
          self.start_time = None
     def _init_camera(self) -> bool:
          """khởi tạo và cấu hình camera"""
          try:
               self.cap = cv2.VideoCapture(self.camera_index)
               if not self.cap.isOpened():
                    print(f"❌ Không thể mở camera với index {self.camera_index}")
                    return False
               # cấu hình camera nếu cần
               self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
               self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
               self.cap.set(cv2.CAP_PROP_FPS, 30)
               ret , frame = self.cap.read()
               if not ret:
                    print("❌ Không thể đọc frame từ camera")
                    return False
               return True
          except Exception as e:
               print(f"❌ Lỗi khởi tạo camera: {e}")
               return False
     def run(self):
          """vòng lặp chính - chạy khi gọi thread.start()"""
          if not self._init_camera():
               print("không thể khởi tạo camera, thread dừng")
               return
          self.running = True
          self.start_time = time.time()
          print("✅ Camera thread started")
          while self.running:
               ret , frame = self.cap.read()
               if not ret:
                    print("❌ Không thể đọc frame từ camera, dừng thread")
                    break
               # tính fps
               self.frame_count += 1
               elapsed_time = time.time() - self.start_time
               if elapsed_time >= 1.0:
                    self.fps = self.frame_count / elapsed_time
                    self.frame_count = 0
                    self.start_time = time.time()
               # gửi frame vào queue
               try:
                    if not self.frame_queue.full():
                         try : self.frame_queue.get_nowait()
                         except Empty:
                              pass
                    self.frame_queue.put(frame , block=False)
               except Full:
                    # nếu queue đầy, bỏ qua frame này
                    pass
               except Exception as e:
                    print(f"❌ Lỗi khi đưa frame vào queue: {e}")
          self._cleanup()
          print("🛑 Camera thread stopped")
     def stop(self):
          self.running = False
     def _cleanup(self):
          """giải phóng tài nguyên"""
          if self.cap and self.cap.isOpened():
               self.cap.release()
     def get_fps(self) -> float:
          """lấy fps hiện tại"""
          return self.fps