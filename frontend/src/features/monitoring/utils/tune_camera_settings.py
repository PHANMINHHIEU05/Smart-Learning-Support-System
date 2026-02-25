#!/usr/bin/env python3
"""
Tool để điều chỉnh camera settings realtime
Giúp tìm giá trị exposure/brightness/gain tối ưu cho hệ thống giám sát học tập
"""
import cv2
import subprocess
import time

def set_camera_controls(exposure, brightness, gain):
    """Đặt camera controls qua v4l2-ctl"""
    try:
        subprocess.run(
            ['v4l2-ctl', '-d', '/dev/video0',
             f'--set-ctrl=auto_exposure=1,exposure_time_absolute={exposure},brightness={brightness},gain={gain}'],
            capture_output=True, timeout=2
        )
    except Exception:
        pass

def main():
    # Thiết lập ban đầu
    exposure = 200
    brightness = 150
    gain = 50
    
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # OpenCV controls
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
    cap.set(cv2.CAP_PROP_GAIN, gain)
    
    # v4l2-ctl controls
    set_camera_controls(exposure, brightness, gain)
    
    print("=== Camera Settings Tuner ===")
    print("Phím điều khiển:")
    print("  E/e: Exposure +10/-10 (càng cao = càng sáng, giới hạn FPS)")
    print("  B/b: Brightness +10/-10 (độ sáng tổng thể)")
    print("  G/g: Gain +5/-5 (tăng cường độ sáng)")
    print("  R: Reset về mặc định")
    print("  Q: Thoát và lưu giá trị vào config")
    print()
    
    fps_count = 0
    fps_start = time.time()
    current_fps = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Tính FPS
        fps_count += 1
        elapsed = time.time() - fps_start
        if elapsed >= 1.0:
            current_fps = fps_count / elapsed
            fps_count = 0
            fps_start = time.time()
        
        # Hiển thị thông tin
        info_frame = frame.copy()
        y = 30
        cv2.putText(info_frame, f"FPS: {current_fps:.1f}", (20, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y += 30
        cv2.putText(info_frame, f"Exposure: {exposure}", (20, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        y += 30
        cv2.putText(info_frame, f"Brightness: {brightness}", (20, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        y += 30
        cv2.putText(info_frame, f"Gain: {gain}", (20, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        y += 40
        cv2.putText(info_frame, "E/e B/b G/g R Q", (20, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        cv2.imshow("Camera Settings Tuner", info_frame)
        
        key = cv2.waitKey(1) & 0xFF
        changed = False
        
        if key == ord('q'):
            break
        elif key == ord('E'):
            exposure = min(300, exposure + 10)
            changed = True
        elif key == ord('e'):
            exposure = max(50, exposure - 10)
            changed = True
        elif key == ord('B'):
            brightness = min(255, brightness + 10)
            changed = True
        elif key == ord('b'):
            brightness = max(0, brightness - 10)
            changed = True
        elif key == ord('G'):
            gain = min(100, gain + 5)
            changed = True
        elif key == ord('g'):
            gain = max(0, gain - 5)
            changed = True
        elif key == ord('r'):
            exposure = 200
            brightness = 150
            gain = 50
            changed = True
            print("Reset về mặc định")
        
        if changed:
            cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
            cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
            cap.set(cv2.CAP_PROP_GAIN, gain)
            set_camera_controls(exposure, brightness, gain)
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n=== Giá trị cuối cùng ===")
    print(f"CAMERA_EXPOSURE_VALUE = {exposure}")
    print(f"CAMERA_BRIGHTNESS = {brightness}")
    print(f"CAMERA_GAIN = {gain}")
    print(f"FPS: {current_fps:.1f}")
    print("\nCopy các giá trị này vào config/performance_config.py")

if __name__ == "__main__":
    main()
