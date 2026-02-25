"""Benchmark camera with different strategies to find fastest"""
import cv2
import time
import subprocess
import sys

cam_idx = 0

def measure_fps(cap, label, num_frames=30):
    """Đo FPS thực tế"""
    if not cap.isOpened():
        print(f"  [{label}] FAIL - cannot open")
        return 0
    for _ in range(5):
        cap.read()
    t0 = time.time()
    ok = 0
    for _ in range(num_frames):
        ret, _ = cap.read()
        if ret:
            ok += 1
    elapsed = time.time() - t0
    fps = ok / elapsed if elapsed > 0 else 0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  [{label}] {w}x{h} -> {fps:.1f} FPS ({ok}/{num_frames} in {elapsed:.2f}s)")
    return fps

print("=" * 60)
print("CAMERA BENCHMARK")
print("=" * 60)

# TEST 1: Manual exposure
print("\nTest 1: Manual exposure (fast shutter)")
try:
    subprocess.run(["v4l2-ctl", "-d", f"/dev/video{cam_idx}",
                     "--set-ctrl=auto_exposure=1",
                     "--set-ctrl=exposure_time_absolute=100"],
                    capture_output=True, timeout=5)
    print("  Set manual exposure OK")
except Exception as e:
    print(f"  v4l2-ctl failed: {e}")

cap = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
fps1 = measure_fps(cap, "V4L2+MJPG+ManualExp")
cap.release()

try:
    subprocess.run(["v4l2-ctl", "-d", f"/dev/video{cam_idx}",
                     "--set-ctrl=auto_exposure=3"],
                    capture_output=True, timeout=5)
except Exception:
    pass

# TEST 2: GStreamer pipeline
print("\nTest 2: GStreamer pipeline")
gst_pipes = [
    ("GStreamer MJPG 640", f"v4l2src device=/dev/video{cam_idx} ! image/jpeg,width=640,height=480,framerate=30/1 ! jpegdec ! videoconvert ! appsink"),
    ("GStreamer YUYV 640", f"v4l2src device=/dev/video{cam_idx} ! video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 ! videoconvert ! appsink"),
]
for label, pipeline in gst_pipes:
    try:
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        measure_fps(cap, label)
        cap.release()
    except Exception as e:
        print(f"  [{label}] ERROR: {e}")

# TEST 3: OpenCV exposure control
print("\nTest 3: OpenCV exposure control")
cap = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
cap.set(cv2.CAP_PROP_EXPOSURE, 100)
measure_fps(cap, "OpenCV ManualExp")
cap.release()

# TEST 4: video1
print(f"\nTest 4: /dev/video1")
try:
    cap = cv2.VideoCapture(1, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    measure_fps(cap, "video1 MJPG")
    cap.release()
except Exception as e:
    print(f"  [video1] ERROR: {e}")

print("\nDone!")
