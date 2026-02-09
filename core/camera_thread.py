import cv2 
import threading
import time
import subprocess
from queue import Queue, Full, Empty
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import performance_config as perf


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
        
        # Thread-safe latest frame cho display (không cần qua AI queue)
        self._latest_frame = None
        self._frame_lock = threading.Lock()

    def get_latest_frame(self):
        """Lấy frame mới nhất - thread-safe, không block"""
        with self._frame_lock:
            return self._latest_frame

    def _apply_manual_exposure(self, cap):
        """Áp dụng manual exposure để tối ưu FPS + tăng độ sáng.
        
        Auto-exposure thường chọn shutter speed chậm → giảm FPS xuống 5.
        Manual exposure với giá trị cao hơn giữ FPS ở mức 15+ VÀ hình sáng đẹp.
        """
        if not getattr(perf, 'CAMERA_MANUAL_EXPOSURE', True):
            return
        
        exposure_value = getattr(perf, 'CAMERA_EXPOSURE_VALUE', 200)
        brightness = getattr(perf, 'CAMERA_BRIGHTNESS', 150)
        gain = getattr(perf, 'CAMERA_GAIN', 50)
        
        # Đặt qua OpenCV
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 1 = Manual mode
        cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
        cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
        cap.set(cv2.CAP_PROP_GAIN, gain)
        
        # Linux: cũng đặt qua v4l2-ctl để chắc chắn
        if sys.platform.startswith("linux"):
            try:
                subprocess.run(
                    ['v4l2-ctl', '-d', f'/dev/video{self.camera_index}',
                     f'--set-ctrl=auto_exposure=1,exposure_time_absolute={exposure_value},brightness={brightness},gain={gain}'],
                    capture_output=True, timeout=2
                )
            except Exception:
                pass  # v4l2-ctl có thể không có, bỏ qua
    
    def _init_camera(self) -> bool:
        try:
            # === THỬ NHIỀU CÁCH MỞ CAMERA ĐỂ TÌM CÁI NHANH NHẤT ===
            configs = []
            
            if sys.platform.startswith("linux"):
                # Linux: thử MJPG + V4L2 trước (thường nhanh nhất)
                configs.append(("V4L2+MJPG", cv2.CAP_V4L2, 'MJPG'))
                configs.append(("V4L2+YUYV", cv2.CAP_V4L2, None))
                configs.append(("Default", cv2.CAP_ANY, None))
            elif sys.platform.startswith("win"):
                configs.append(("DSHOW+MJPG", cv2.CAP_DSHOW, 'MJPG'))
                configs.append(("DSHOW", cv2.CAP_DSHOW, None))
                configs.append(("Default", cv2.CAP_ANY, None))
            else:
                configs.append(("Default+MJPG", cv2.CAP_ANY, 'MJPG'))
                configs.append(("Default", cv2.CAP_ANY, None))
            
            best_cap = None
            best_fps = 0
            best_name = ""
            
            for name, backend, fourcc in configs:
                try:
                    cap = cv2.VideoCapture(self.camera_index, backend)
                    if not cap.isOpened():
                        cap.release()
                        continue
                    
                    # Set codec trước resolution
                    if fourcc:
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
                    
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, perf.CAMERA_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, perf.CAMERA_HEIGHT)
                    cap.set(cv2.CAP_PROP_FPS, perf.CAMERA_FPS)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    # Áp dụng manual exposure để tối ưu FPS
                    self._apply_manual_exposure(cap)
                    
                    # Đo FPS thực tế bằng cách đọc vài frame
                    # Warm up
                    for _ in range(5):
                        cap.read()
                    
                    t0 = time.time()
                    ok_count = 0
                    for _ in range(15):
                        ret, _ = cap.read()
                        if ret:
                            ok_count += 1
                    elapsed = time.time() - t0
                    
                    if ok_count < 5:
                        cap.release()
                        continue
                    
                    measured_fps = ok_count / elapsed if elapsed > 0 else 0
                    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"  📷 [{name}] {actual_w}x{actual_h} → {measured_fps:.1f} FPS thực tế")
                    
                    if measured_fps > best_fps:
                        if best_cap:
                            best_cap.release()
                        best_cap = cap
                        best_fps = measured_fps
                        best_name = name
                    else:
                        cap.release()
                    
                    # Nếu đạt FPS tốt (>10), dùng luôn, không cần thử thêm
                    if best_fps >= 10:
                        break
                        
                except Exception:
                    continue
            
            if best_cap is None:
                # Fallback cuối cùng
                best_cap = cv2.VideoCapture(self.camera_index)
                if not best_cap.isOpened():
                    print(f"❌ Không thể mở camera {self.camera_index}")
                    return False
                best_name = "Fallback"
            
            self.cap = best_cap
            
            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            print(f"✅ Chọn camera: [{best_name}] {actual_w}x{actual_h} @ {actual_fps:.0f} FPS (thực tế {best_fps:.1f} FPS)")
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
            
            # Lưu frame mới nhất cho display (luôn có frame mới nhất)
            with self._frame_lock:
                self._latest_frame = frame
            
            # Tính FPS
            self.frame_count += 1
            elapsed = time.time() - self.start_time
            if elapsed >= 1.0:
                self.fps = self.frame_count / elapsed
                self.frame_count = 0
                self.start_time = time.time()
            
            # Gửi frame vào queue cho AI (drop frame cũ nếu full)
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
