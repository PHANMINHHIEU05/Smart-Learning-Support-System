#!/usr/bin/env python3
"""
Script tối ưu FPS nhanh - Bật/tắt các features để tăng FPS
"""

import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def modify_config(key, value):
    """Sửa giá trị trong performance_config.py"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config', 'performance_config.py'
    )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace value
    pattern = f"{key} = .*"
    replacement = f"{key} = {value}"
    new_content = re.sub(pattern, replacement, content)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Đã set {key} = {value}")

def show_current_settings():
    """Hiển thị settings hiện tại"""
    from config import performance_config as perf
    
    print("\n" + "="*60)
    print("🎮 CÀI ĐẶT HIỆN TẠI")
    print("="*60)
    print(f"📹 Processing: {perf.PROCESSING_WIDTH}x{perf.PROCESSING_HEIGHT}")
    print(f"🔄 Face Interval: 1/{perf.FACE_PROCESS_INTERVAL}")
    print(f"🧍 Pose Interval: 1/{perf.POSE_PROCESS_INTERVAL}")
    print(f"🔍 Advanced Interval: 1/{perf.ADVANCED_STATE_INTERVAL}")
    print(f"\n📊 FEATURES:")
    print(f"  • Pose Detection: {perf.ENABLE_POSE_DETECTION}")
    print(f"  • Blendshapes: {perf.ENABLE_BLENDSHAPES}")
    print(f"  • Advanced States: {perf.ENABLE_ADVANCED_STATES}")
    print(f"  • Microsleep: {perf.ENABLE_MICROSLEEP}")
    print("="*60 + "\n")

def ultra_performance_mode():
    """Chế độ MAX FPS - tắt mọi thứ không cần thiết"""
    print("\n🚀 ÁP DỤNG ULTRA PERFORMANCE MODE...")
    print("="*60)
    
    modify_config("PROCESSING_WIDTH", "256")
    modify_config("PROCESSING_HEIGHT", "192")
    modify_config("FACE_PROCESS_INTERVAL", "4")
    modify_config("POSE_PROCESS_INTERVAL", "6")
    modify_config("ADVANCED_STATE_INTERVAL", "30")
    modify_config("ENABLE_POSE_DETECTION", "False")
    modify_config("ENABLE_BLENDSHAPES", "False")
    modify_config("ENABLE_ADVANCED_STATES", "False")
    
    print("\n✅ ĐÃ BẬT ULTRA PERFORMANCE!")
    print("📊 Dự kiến FPS: 40-60 FPS")
    print("⚠️  Chú ý: Chỉ có face detection và drowsiness")
    print("🔄 Khởi động lại ứng dụng để áp dụng!\n")

def performance_mode():
    """Chế độ High Performance - tắt pose và blendshapes"""
    print("\n🏃 ÁP DỤNG HIGH PERFORMANCE MODE...")
    print("="*60)
    
    modify_config("PROCESSING_WIDTH", "256")
    modify_config("PROCESSING_HEIGHT", "192")
    modify_config("FACE_PROCESS_INTERVAL", "3")
    modify_config("POSE_PROCESS_INTERVAL", "5")
    modify_config("ADVANCED_STATE_INTERVAL", "20")
    modify_config("ENABLE_POSE_DETECTION", "False")
    modify_config("ENABLE_BLENDSHAPES", "True")
    modify_config("ENABLE_ADVANCED_STATES", "True")
    
    print("\n✅ ĐÃ BẬT HIGH PERFORMANCE!")
    print("📊 Dự kiến FPS: 30-40 FPS")
    print("⚠️  Chú ý: Không có posture detection")
    print("🔄 Khởi động lại ứng dụng để áp dụng!\n")

def balanced_mode():
    """Chế độ cân bằng - bật đầy đủ nhưng interval cao"""
    print("\n⚖️  ÁP DỤNG BALANCED MODE...")
    print("="*60)
    
    modify_config("PROCESSING_WIDTH", "320")
    modify_config("PROCESSING_HEIGHT", "240")
    modify_config("FACE_PROCESS_INTERVAL", "2")
    modify_config("POSE_PROCESS_INTERVAL", "3")
    modify_config("ADVANCED_STATE_INTERVAL", "15")
    modify_config("ENABLE_POSE_DETECTION", "True")
    modify_config("ENABLE_BLENDSHAPES", "True")
    modify_config("ENABLE_ADVANCED_STATES", "True")
    
    print("\n✅ ĐÃ BẬT BALANCED MODE!")
    print("📊 Dự kiến FPS: 25-30 FPS")
    print("✨ Đầy đủ tính năng")
    print("🔄 Khởi động lại ứng dụng để áp dụng!\n")

def full_features_mode():
    """Chế độ đầy đủ tính năng - ưu tiên accuracy"""
    print("\n🎯 ÁP DỤNG FULL FEATURES MODE...")
    print("="*60)
    
    modify_config("PROCESSING_WIDTH", "320")
    modify_config("PROCESSING_HEIGHT", "240")
    modify_config("FACE_PROCESS_INTERVAL", "1")
    modify_config("POSE_PROCESS_INTERVAL", "1")
    modify_config("ADVANCED_STATE_INTERVAL", "10")
    modify_config("ENABLE_POSE_DETECTION", "True")
    modify_config("ENABLE_BLENDSHAPES", "True")
    modify_config("ENABLE_ADVANCED_STATES", "True")
    
    print("\n✅ ĐÃ BẬT FULL FEATURES!")
    print("📊 Dự kiến FPS: 15-20 FPS")
    print("✨ Accuracy cao nhất")
    print("🔄 Khởi động lại ứng dụng để áp dụng!\n")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("\n" + "="*60)
        print("🚀 FPS OPTIMIZATION TOOL")
        print("="*60)
        show_current_settings()
        
        print("💡 SỬ DỤNG:")
        print("   python utils/fps_boost.py [mode]\n")
        print("📌 CÁC MODES:")
        print("   ultra     - FPS cao nhất (40-60 FPS) - CHỈ face detection")
        print("   fast      - High performance (30-40 FPS) - Không posture")
        print("   balanced  - Cân bằng (25-30 FPS) - Đầy đủ tính năng")
        print("   full      - Accuracy cao (15-20 FPS) - Process mọi frame")
        print("   current   - Xem settings hiện tại")
        print("\n📌 VÍ DỤ:")
        print("   python utils/fps_boost.py ultra")
        print("   python utils/fps_boost.py fast")
        print("   python utils/fps_boost.py balanced")
        print()
        return
    
    mode = sys.argv[1].lower()
    
    if mode in ['ultra', 'max', 'fastest']:
        ultra_performance_mode()
    elif mode in ['fast', 'performance', 'high']:
        performance_mode()
    elif mode in ['balanced', 'default', 'normal']:
        balanced_mode()
    elif mode in ['full', 'accuracy', 'complete']:
        full_features_mode()
    elif mode in ['current', 'show', 'status']:
        show_current_settings()
    else:
        print(f"❌ Mode '{mode}' không tồn tại!")
        print("📋 Modes có sẵn: ultra, fast, balanced, full, current")

if __name__ == "__main__":
    main()
