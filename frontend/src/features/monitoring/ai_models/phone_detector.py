import cv2
import numpy as np
from typing import Dict, List, Tuple
from ultralytics import YOLO
import torch

class PhoneDetector:
    def __init__(self,
                 model_name: str = 'yolo11n.pt',
                 confidence_threshold: float = 0.40,
                 phone_frames: int = 5):
        """
        Lớp nhận diện điện thoại tối ưu cho YOLO11 Nano.
        Args:
            model_name: Tên model (sẽ tự tải yolo11n.pt nếu chưa có).
            confidence_threshold: Độ tin cậy tối thiểu (0.40 là mức cân bằng tốt).
            phone_frames: Số khung hình liên tục để kích hoạt trạng thái 'Đang dùng điện thoại'.
        """
        # 1. Load Model
        self.model = YOLO(model_name)
        
        # 2. Tối ưu hóa phần cứng (Sử dụng GPU nếu có CUDA, không thì dùng CPU)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        
        # 3. Fuse layers để tăng tốc độ inference (chỉ làm 1 lần lúc init)
        self.model.fuse()
        
        # 4. Cấu hình logic
        self.conf_threshold = confidence_threshold
        self.phone_frames = phone_frames
        self.phone_counter = 0
        self.is_using_phone = False
        
        # Class ID của điện thoại trong bộ COCO là 67
        self.PHONE_CLS_ID = 67 

    def process(self, frame: np.ndarray) -> Tuple[bool, float, List[Dict]]:
        """
        Xử lý khung hình và trả về kết quả.
        Returns:
            - is_using_phone (bool): Trạng thái cuối cùng sau khi qua bộ lọc counter.
            - confidence (float): Độ tin cậy của điện thoại rõ nhất (0-100).
            - detections (list): Danh sách các bbox để vẽ lên màn hình nếu cần.
        """
        # Inference với các tham số tối ưu cho tốc độ
        # imgsz=320 giúp chạy cực nhanh trên CPU
        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            classes=[self.PHONE_CLS_ID],
            imgsz=320,
            half=(self.device != 'cpu'), # Dùng FP16 nếu chạy GPU
            verbose=False,
            stream=False
        )

        detections = []
        highest_conf = 0.0
        phone_in_this_frame = False

        # Parse kết quả
        for r in results:
            boxes = r.boxes
            if len(boxes) > 0:
                phone_in_this_frame = True
                for i in range(len(boxes)):
                    conf = float(boxes.conf[i])
                    highest_conf = max(highest_conf, conf)
                    
                    # Lấy tọa độ bbox (x1, y1, x2, y2)
                    xyxy = boxes.xyxy[i].cpu().numpy().astype(int)
                    detections.append({
                        'bbox': tuple(xyxy),
                        'conf': conf
                    })

        # --- LOGIC BỘ LỌC (COUNTER) ---
        # Giúp tránh báo động giả khi điện thoại chỉ lướt qua
        if phone_in_this_frame:
            # Tăng nhanh (+2) để bắt kịp hành động cầm máy
            self.phone_counter = min(self.phone_frames * 2, self.phone_counter + 2)
        else:
            # Giảm chậm (-1) để giữ trạng thái nếu frame bị mờ hoặc rung
            self.phone_counter = max(0, self.phone_counter - 1)

        # Trạng thái cuối cùng
        self.is_using_phone = self.phone_counter >= self.phone_frames

        return self.is_using_phone, highest_conf * 100, detections

    def reset(self):
        """Reset trạng thái về ban đầu"""
        self.phone_counter = 0
        self.is_using_phone = False

# --- ĐOẠN CODE TEST NHANH ---
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    detector = PhoneDetector()
    
    print("🚀 Đang chạy test... Nhấn 'q' để thoát.")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        is_phone, conf, dets = detector.process(frame)
        
        # Vẽ lên màn hình để kiểm tra
        color = (0, 0, 255) if is_phone else (0, 255, 0)
        status_text = f"PHONE: {is_phone} ({conf:.1f}%)"
        
        for d in dets:
            x1, y1, x2, y2 = d['bbox']
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
        cv2.putText(frame, status_text, (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        cv2.imshow("YOLO11 Phone Monitor", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()