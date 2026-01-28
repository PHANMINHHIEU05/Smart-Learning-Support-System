from typing import List, Tuple, Optional, Dict
from ultralytics import YOLO
import numpy as np

CELL_PHONE_CLASS_ID = 67  # cell phone
PERSON_CLASS_ID = 0       # person (optional)


class PhoneDetector:
    def __init__(self,
                 model_name: str = 'yolov8n.pt',
                 confidence_threshold: float = 0.35,
                 phone_frames: int = 5):
        self.model = YOLO(model_name)
        self.confidence_threshold = confidence_threshold
        self.phone_frames = phone_frames
        self.phone_counter = 0
        self.is_using_phone = False
        self.phone_bbox = None
        self.last_frame_height = 480
        self.debug = False  # Set True để debug

    def detect(self, frame) -> List[Dict]:
        self.last_frame_height = frame.shape[0]
        results = self.model(frame, verbose=False, classes=[CELL_PHONE_CLASS_ID])
        
        detections = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                if conf >= self.confidence_threshold:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    
                    detections.append({
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': (x1, y1, x2, y2),
                        'center': (cx, cy)
                    })
                    
                    if self.debug:
                        print(f"📱 Phone detected: conf={conf:.2f}, bbox={x1},{y1},{x2},{y2}")
        
        return detections

    def _is_phone_near_face(self) -> bool:
        """Check if phone is in upper half of frame (near face area)"""
        if self.phone_bbox is None:
            return False
        x1, y1, x2, y2 = self.phone_bbox
        phone_center_y = (y1 + y2) / 2
        # Phone ở nửa trên của frame = gần mặt
        near_face = phone_center_y < self.last_frame_height * 0.7  # Mở rộng vùng từ 0.5 -> 0.7
        return near_face

    def process(self, frame) -> Tuple[bool, float, Optional[List]]:
        detections = self.detect(frame)
        
        phone_detected = False
        phone_confidence = 0.0
        self.phone_bbox = None
        
        for det in detections:
            if det['class_id'] == CELL_PHONE_CLASS_ID:
                phone_detected = True
                self.phone_bbox = det['bbox']
                phone_confidence = det['confidence']
                break
        
        # Nếu phát hiện phone (không cần check near face ban đầu)
        if phone_detected:
            self.phone_counter += 2  # Tăng nhanh hơn
            if self.debug:
                print(f"📱 Counter: {self.phone_counter}/{self.phone_frames}")
        else:
            self.phone_counter = max(0, self.phone_counter - 1)  # Giảm dần
        
        self.is_using_phone = self.phone_counter >= self.phone_frames
        return self.is_using_phone, phone_confidence * 100, detections  # Return % confidence

    def reset(self):
        self.phone_counter = 0
        self.is_using_phone = False
        self.phone_bbox = None