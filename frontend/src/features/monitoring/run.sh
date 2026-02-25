#!/bin/bash
# Smart Learning Support System - Run Script
# Đường dẫn: /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend/src/features/monitoring

cd "$(dirname "$0")"

echo "=========================================="
echo "  Smart Learning Support System"
echo "  Camera Monitoring"
echo "=========================================="
echo ""

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found!"
    echo "   Run: python -m venv venv"
    exit 1
fi

# Check camera
echo "📷 Checking camera..."
python -c "import cv2; cap = cv2.VideoCapture(0); print('✅ Camera OK' if cap.isOpened() else '❌ Camera not found'); cap.release()" || exit 1

echo ""
echo "🚀 Starting application..."
echo "   Press 'q' to quit"
echo "   Press 'c' to calibrate"
echo ""

# Run main app
python main.py

# Cleanup
deactivate
echo ""
echo "✅ Application stopped"
