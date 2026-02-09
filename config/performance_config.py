"""
Performance Configuration for Smart Learning Support System
Tối ưu FPS và Performance
"""

# ============ CAMERA SETTINGS ============
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CAMERA_BUFFER_SIZE = 1  # Giảm buffer để giảm latency

# Camera exposure settings
# Auto-exposure thường chọn shutter chậm → FPS thấp (5 FPS)
# Manual exposure giữ FPS cao (~15 FPS) + tăng exposure value để sáng hơn
CAMERA_MANUAL_EXPOSURE = True       # True = manual exposure (giữ FPS), False = auto (lag)
CAMERA_EXPOSURE_VALUE = 225     # Giá trị exposure (50-300, cao = sáng hơn)
CAMERA_BRIGHTNESS = 160           # Brightness (0-255, mặc định 128)
CAMERA_GAIN = 40                  # Gain để tăng độ sáng (0-100)

# ============ PROCESSING SETTINGS ============
# Resolution để xử lý AI (nhỏ hơn camera resolution)
PROCESSING_WIDTH = 256
PROCESSING_HEIGHT = 192
PROCESSING_SCALE = 0.5  # Scale factor từ camera resolution

# Frame skipping để tăng FPS - TĂNG MẠNH
FACE_PROCESS_INTERVAL = 3
POSE_PROCESS_INTERVAL = 6
BLENDSHAPE_PROCESS_INTERVAL = 3  # TĂNG: 2→3 frames

# Advanced features interval
ADVANCED_STATE_INTERVAL = 20
# EMOTION_UPDATE_INTERVAL = 45  # ĐÃ TẮT: Không dùng emotion detection nữa

# ============ MEDIAPIPE SETTINGS ============
# Face Landmarker
FACE_DETECTION_CONFIDENCE = 0.25
FACE_PRESENCE_CONFIDENCE = 0.25   # GIẢM: 0.3→0.25
FACE_TRACKING_CONFIDENCE = 0.25   # GIẢM: 0.3→0.25
FACE_NUM_FACES = 1

# Pose Landmarker  
POSE_DETECTION_CONFIDENCE = 0.25
POSE_PRESENCE_CONFIDENCE = 0.25   # GIẢM: 0.3→0.25
POSE_TRACKING_CONFIDENCE = 0.25   # GIẢM: 0.3→0.25

# Blendshapes optimization
USE_SELECTIVE_BLENDSHAPES = True  # Chỉ lấy blendshapes quan trọng
IMPORTANT_BLENDSHAPES = [
    'mouthSmileLeft', 'mouthSmileRight',      # Happy
    'mouthFrownLeft', 'mouthFrownRight',      # Sad
    'browInnerUp',                             # Surprise/Fear
    'browDownLeft', 'browDownRight',          # Angry
    'eyeSquintLeft', 'eyeSquintRight',        # Disgust/Happy
    'jawOpen', 'mouthFunnel',                 # Surprise
    'cheekSquintLeft', 'cheekSquintRight',    # Happy
    'noseSneerLeft', 'noseSneerRight',        # Disgust
    'mouthPressLeft', 'mouthPressRight',      # Angry
    'mouthUpperUpLeft', 'mouthUpperUpRight',  # Disgust
]

# ============ QUEUE SETTINGS ============
FRAME_QUEUE_SIZE = 2
RESULT_QUEUE_SIZE = 2

# ============ DISPLAY SETTINGS ============
DISPLAY_WIDTH = 640   # Resolution hiển thị (có thể khác processing)
DISPLAY_HEIGHT = 480
DISPLAY_FPS_LIMIT = 30  # Giới hạn FPS hiển thị - giờ có thể cao vì đã tách AI

# ============ OPTIMIZATION FLAGS ============
ENABLE_FRAME_SKIPPING = True  # Bật frame skipping
ENABLE_RESULT_CACHING = True  # Cache kết quả khi skip frames
ENABLE_SMART_RESIZE = True    # Resize thông minh (1 lần thay vì nhiều lần)

# Performance monitoring
SHOW_FPS = True
SHOW_PERFORMANCE_METRICS = False  # Chi tiết timing mỗi component

# ============ FEATURE FLAGS ============
# Tắt features không cần thiết để tăng FPS
ENABLE_PHONE_DETECTION = False  # Đã tắt
ENABLE_POSE_DETECTION = True
ENABLE_MICROSLEEP = True
ENABLE_ADVANCED_STATES = True
ENABLE_EMOTION_DETECTION = False  # ĐÃ TẮT - Không phân tích cảm xúc
ENABLE_BLENDSHAPES = True  # Vẫn bật để dùng cho các tính năng khác (nếu cần)

# ============ PRESETS ============
def get_preset(preset_name: str) -> dict:
    """Lấy preset configuration
    
    Presets:
    - 'high_performance': FPS cao nhất, accuracy thấp hơn
    - 'balanced': Cân bằng FPS và accuracy
    - 'high_accuracy': Accuracy cao nhất, FPS thấp hơn
    - 'web_mvp': Ưu tiên mượt khi stream lên web
    - 'web_full': Đầy đủ tính năng hơn cho web
    """
    presets = {
        'high_performance': {
            'CAMERA_WIDTH': 320,
            'CAMERA_HEIGHT': 240,
            'PROCESSING_WIDTH': 224,
            'PROCESSING_HEIGHT': 168,
            'FACE_PROCESS_INTERVAL': 4,
            'POSE_PROCESS_INTERVAL': 8,
            'ADVANCED_STATE_INTERVAL': 30,
            'FACE_DETECTION_CONFIDENCE': 0.20,
            'POSE_DETECTION_CONFIDENCE': 0.20,
            'ENABLE_POSE_DETECTION': False,
            'ENABLE_BLENDSHAPES': False,
            'ENABLE_ADVANCED_STATES': False,
            'ENABLE_MICROSLEEP': True,
        },
        'balanced': {
            'CAMERA_WIDTH': 640,
            'CAMERA_HEIGHT': 480,
            'PROCESSING_WIDTH': 256,
            'PROCESSING_HEIGHT': 192,
            'FACE_PROCESS_INTERVAL': 3,
            'POSE_PROCESS_INTERVAL': 4,
            'ADVANCED_STATE_INTERVAL': 20,
            'FACE_DETECTION_CONFIDENCE': 0.25,
            'POSE_DETECTION_CONFIDENCE': 0.25,
            'ENABLE_POSE_DETECTION': True,
            'ENABLE_BLENDSHAPES': True,
            'ENABLE_ADVANCED_STATES': True,
            'ENABLE_MICROSLEEP': True,
        },
        'high_accuracy': {
            'CAMERA_WIDTH': 640,
            'CAMERA_HEIGHT': 480,
            'CAMERA_FPS': 30,
            'PROCESSING_WIDTH': 480,
            'PROCESSING_HEIGHT': 360,
            'FACE_PROCESS_INTERVAL': 1,
            'POSE_PROCESS_INTERVAL': 1,
            'ADVANCED_STATE_INTERVAL': 5,
            'FACE_DETECTION_CONFIDENCE': 0.5,
            'POSE_DETECTION_CONFIDENCE': 0.5,
            'ENABLE_POSE_DETECTION': True,
            'ENABLE_BLENDSHAPES': True,
            'ENABLE_ADVANCED_STATES': True,
            'ENABLE_MICROSLEEP': True,
        },
        'web_mvp': {
            'CAMERA_WIDTH': 640,
            'CAMERA_HEIGHT': 480,
            'CAMERA_FPS': 20,
            'PROCESSING_WIDTH': 224,
            'PROCESSING_HEIGHT': 168,
            'FACE_PROCESS_INTERVAL': 4,
            'POSE_PROCESS_INTERVAL': 8,
            'ADVANCED_STATE_INTERVAL': 30,
            'FACE_DETECTION_CONFIDENCE': 0.20,
            'POSE_DETECTION_CONFIDENCE': 0.20,
            'FRAME_QUEUE_SIZE': 2,
            'RESULT_QUEUE_SIZE': 2,
            'DISPLAY_FPS_LIMIT': 20,
            'ENABLE_POSE_DETECTION': False,
            'ENABLE_BLENDSHAPES': False,
            'ENABLE_ADVANCED_STATES': False,
            'ENABLE_MICROSLEEP': True,
        },
        'web_full': {
            'CAMERA_WIDTH': 640,
            'CAMERA_HEIGHT': 480,
            'CAMERA_FPS': 20,
            'PROCESSING_WIDTH': 256,
            'PROCESSING_HEIGHT': 192,
            'FACE_PROCESS_INTERVAL': 3,
            'POSE_PROCESS_INTERVAL': 6,
            'ADVANCED_STATE_INTERVAL': 20,
            'FACE_DETECTION_CONFIDENCE': 0.25,
            'POSE_DETECTION_CONFIDENCE': 0.25,
            'FRAME_QUEUE_SIZE': 2,
            'RESULT_QUEUE_SIZE': 2,
            'DISPLAY_FPS_LIMIT': 20,
            'ENABLE_POSE_DETECTION': True,
            'ENABLE_BLENDSHAPES': True,
            'ENABLE_ADVANCED_STATES': True,
            'ENABLE_MICROSLEEP': True,
        },
    }
    return presets.get(preset_name, presets['balanced'])

# Default: Balanced preset
ACTIVE_PRESET = 'web_full'
