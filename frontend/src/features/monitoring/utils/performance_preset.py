#!/usr/bin/env python3
"""
Script đổi preset performance config
Presets: high_performance, balanced, high_accuracy, web_mvp, web_full
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import performance_config as perf

def show_current_config():
    """Hiển thị cấu hình hiện tại"""
    print("\n" + "="*60)
    print("🔧 PERFORMANCE CONFIGURATION HIỆN TẠI")
    print("="*60)
    print(f"📹 Camera: {perf.CAMERA_WIDTH}x{perf.CAMERA_HEIGHT} @ {perf.CAMERA_FPS}fps")
    print(f"⚙️  Processing: {perf.PROCESSING_WIDTH}x{perf.PROCESSING_HEIGHT}")
    print(f"📊 Face Process Interval: 1/{perf.FACE_PROCESS_INTERVAL} frames")
    print(f"🧍 Pose Process Interval: 1/{perf.POSE_PROCESS_INTERVAL} frames")
    print(f"🔍 Advanced State Interval: 1/{perf.ADVANCED_STATE_INTERVAL} frames")
    print(f"😊 Selective Blendshapes: {perf.USE_SELECTIVE_BLENDSHAPES}")
    print(f"💾 Result Caching: {perf.ENABLE_RESULT_CACHING}")
    print(f"🎯 Active Preset: {perf.ACTIVE_PRESET.upper()}")
    print("="*60 + "\n")

def show_available_presets():
    """Hiển thị các presets có sẵn"""
    print("\n" + "="*60)
    print("📦 PRESETS CÓ SẴN")
    print("="*60)
    
    presets = {
        'high_performance': {
            'name': '🚀 HIGH PERFORMANCE',
            'desc': 'FPS cao nhất (~40-50 FPS), accuracy thấp hơn',
            'use_case': 'Máy yếu, cần mượt mà'
        },
        'balanced': {
            'name': '⚖️ BALANCED (Recommended)',
            'desc': 'Cân bằng FPS và accuracy (~30-35 FPS)',
            'use_case': 'Sử dụng hàng ngày'
        },
        'high_accuracy': {
            'name': '🎯 HIGH ACCURACY',
            'desc': 'Accuracy cao nhất (~20-25 FPS), FPS thấp hơn',
            'use_case': 'Demo, testing, máy mạnh'
        },
        'web_mvp': {
            'name': '🌐 WEB MVP (Recommended)',
            'desc': 'Ưu tiên mượt, nhẹ CPU để stream web ổn định',
            'use_case': 'Deploy web bản đầu tiên'
        },
        'web_full': {
            'name': '🌐 WEB FULL',
            'desc': 'Nhiều tính năng hơn cho web, FPS thấp hơn web_mvp',
            'use_case': 'Web cần posture + advanced states'
        }
    }
    
    for key, info in presets.items():
        print(f"\n{info['name']}")
        print(f"  • Mô tả: {info['desc']}")
        print(f"  • Dùng cho: {info['use_case']}")
        
        # Show config
        preset_config = perf.get_preset(key)
        print(f"  • Config:")
        print(f"    - Processing: {preset_config['PROCESSING_WIDTH']}x{preset_config['PROCESSING_HEIGHT']}")
        print(f"    - Face Interval: 1/{preset_config['FACE_PROCESS_INTERVAL']}")
        print(f"    - Pose Interval: 1/{preset_config['POSE_PROCESS_INTERVAL']}")
    
    print("\n" + "="*60 + "\n")

def apply_preset(preset_name: str):
    """Apply preset vào config file"""
    presets = ['high_performance', 'balanced', 'high_accuracy', 'web_mvp', 'web_full']
    
    if preset_name not in presets:
        print(f"❌ Preset '{preset_name}' không tồn tại!")
        print(f"📋 Presets có sẵn: {', '.join(presets)}")
        return False
    
    # Read config file
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config', 'performance_config.py'
    )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    preset_values = perf.get_preset(preset_name)
    new_content = re.sub(
        r"ACTIVE_PRESET = '[^']*'",
        f"ACTIVE_PRESET = '{preset_name}'",
        content
    )

    def to_python_literal(value):
        if isinstance(value, str):
            return f"'{value}'"
        return str(value)

    # Replace từng biến cấu hình trong preset
    for key, value in preset_values.items():
        pattern = rf"^{key}\s*=.*$"
        replacement = f"{key} = {to_python_literal(value)}"
        new_content, replaced_count = re.subn(
            pattern,
            replacement,
            new_content,
            flags=re.MULTILINE
        )
        if replaced_count == 0:
            new_content += f"\n{replacement}\n"
    
    # Write back
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Đã apply preset: {preset_name.upper()}")
    print(f"🔄 Khởi động lại ứng dụng để áp dụng thay đổi!")
    return True

def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_current_config()
        show_available_presets()
        print("💡 SỬ DỤNG:")
        print("   python utils/performance_preset.py [preset_name]")
        print("\n📌 VÍ DỤ:")
        print("   python utils/performance_preset.py high_performance")
        print("   python utils/performance_preset.py balanced")
        print("   python utils/performance_preset.py high_accuracy")
        print("   python utils/performance_preset.py web_mvp")
        print("   python utils/performance_preset.py web_full")
        return
    
    preset_name = sys.argv[1].lower()
    
    if preset_name in ['show', 'list', 'current']:
        show_current_config()
        show_available_presets()
    else:
        apply_preset(preset_name)

if __name__ == "__main__":
    main()
