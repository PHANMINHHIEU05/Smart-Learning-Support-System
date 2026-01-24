import cv2 
import threading
import time
from queue import Queue, Full, Empty


class CameraThread(threading.Thread):
    """Thread chuyên đọc frame từ camera"""
    
    def __init__(self, camera_index: int = 0, frame_queue: Queue = None):
        super().__init__()
        self.daemon = True
        self.camera_index = camera_index
        self.cap = None
        self.frame_queue = frame_queue if frame_queue else Queue(maxsize=2)
        self.running = False
        self.fps = 0.0
        self.frame_count = 0
        self.start_time = None

    def _init_camera(self) -> bool:
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                print(f"❌ Không thể mở camera {self.camera_index}")
                return False
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            ret, _ = self.cap.read()
            if not ret:
                print("❌ Không thể đọc frame từ camera")
                return False
            return True
        except Exception as e:
            print(f"❌ Lỗi khởi tạo camera: {e}")
            return False

    def run(self):
        if not self._init_camera():
            return
        
        self.running = True
        self.start_time = time.time()
        print("✅ Camera thread started")
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("❌ Không thể đọc frame")
                break
            
            # Tính FPS
            self.frame_count += 1
            elapsed = time.time() - self.start_time
            if elapsed >= 1.0:
                self.fps = self.frame_count / elapsed
                self.frame_count = 0
                self.start_time = time.time()
            
            # Gửi frame vào queue (drop frame cũ nếu full)
            try:
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except Empty:
                        pass
                self.frame_queue.put(frame, block=False)
            except Full:
                pass
        
        self._cleanup()
        print("🛑 Camera thread stopped")

    def stop(self):
        self.running = False

    def _cleanup(self):
        if self.cap:
            self.cap.release()

    def get_fps(self) -> float:
        return self.fps
