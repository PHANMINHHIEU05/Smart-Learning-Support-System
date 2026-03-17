Terminal 1:
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/backend
source ../.venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Terminal 2:

cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend
npm run dev

Terminal 3, chỉ chạy một lần nếu monitoring chưa cài đủ:

cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend/src/features/monitoring
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m pip install httpx

Nếu camera không hiện
Chạy các lệnh này để kiểm tra:
ls -l /dev/video\*
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend/src/features/monitoring
./venv/bin/python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL'); cap.release()"
