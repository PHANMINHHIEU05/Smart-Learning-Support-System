# Hướng dẫn Tích hợp Distraction Monitoring + Pomodoro Timer

**Tác giả**: GitHub Copilot  
**Ngày**: 2024-04-01  
**Phiên bản**: 1.0

---

## 📋 Mục Lục

1. [Tổng Quan Kiến Trúc](#tổng-quan-kiến-trúc)
2. [Backend Integration: NotificationBridge](#backend-integration-notificationbridge)
3. [Frontend Integration: useAlertListener + PomodoroTimer](#frontend-integration-usealerintlistener--pomodorotimer)
4. [Quy Trình Hoạt Động Từ Đầu Đến Cuối](#quy-trình-hoạt-động-từ-đầu-đến-cuối)
5. [Testing & Debugging](#testing--debugging)
6. [Troubleshooting](#troubleshooting)

---

## Tổng Quan Kiến Trúc

### Luồng Dữ Liệu Hoàn Chỉnh

```
┌──────────────┐
│   Browser    │ ← Video frame yêu cầu → ┌──────────────────┐
│   CameraWidget   │                          │  Backend Detect  │
│  (300ms)     │ ← Detect response ← │  Service         │
└──────────────┘ (latest_age_ms<10ms)  └──────────────────┘
                                             ↓
                                        ┌──────────────┐
                                        │ AI Processor │
                                        │  (MediaPipe) │
                                        └──────────────┘
                                             ↓
                    ┌────────────────────────────────────┐
                    │  Caching + Throttling              │
                    │  (intervention_state cache: 0.9s)  │
                    │  (event throttle: 1.0s-2.5s)       │
                    └────────────────────────────────────┘
                                             ↓
                        ┌────────────────────────────────┐
                        │  Alert Triggered               │
                        │  ("focus_lost"|"posture_bad") │
                        └────────────────────────────────┘
                                             ↓
          ┌──────────────────────────────────────────────┐
          │  NotificationBridge                          │
          │  ├─ Desktop Notification (plyer/notify-send) │
          │  ├─ Web Event POST                           │
          │  └─ Thread-safe no-duplicate                 │
          └──────────────────────────────────────────────┘
                                             ↓
                        ┌────────────────────────────────┐
                        │  Websocket/Supabase Realtime   │
                        │  Broadcast to Frontend         │
                        └────────────────────────────────┘
                                             ↓
                  ┌───────────────────────────────────────┐
                  │  useAlertListener Hook                │
                  │  ├─ Receives "alert: start"           │
                  │  ├─ Calls pauseTimer()                │
                  │  └─ Sets isDistracted=true            │
                  └───────────────────────────────────────┘
                                             ↓
                  ┌───────────────────────────────────────┐
                  │  PomodoroTimer Component              │
                  │  ├─ Renders distraction indicator    │
                  │  ├─ Disables Start button            │
                  │  └─ Waits for "alert: stop"          │
                  └───────────────────────────────────────┘
```

### Tập tin Liên Quan

| Tệp                                              | Vai Trò          | Mô Tả                                                   |
| ------------------------------------------------ | ---------------- | ------------------------------------------------------- |
| `backend/app/services/browser_detect_service.py` | Core AI Pipeline | Xử lý frame, chạy MediaPipe, phát hiện xao nhãng        |
| `backend/app/routers/monitoring.py`              | Endpoint Detect  | `/api/detect`: nhận frame, trả về metrics               |
| `backend/app/services/notification_bridge.py`    | Alert Dispatch   | **NEW**: Thông báo xao nhãng đa nền tảng                |
| `frontend/src/hooks/useAlertListener.ts`         | React Hook       | **NEW**: Lắng nghe tín hiệu xao nhãng, điều khiển timer |
| `frontend/src/components/PomodoroTimer.tsx`      | UI Component     | **NEW**: Đồng hồ Pomodoro với chỉ báo xao nhãng         |
| `frontend/src/app/pomodoro/page.tsx`             | Page Demo        | **NEW**: Trang ví dụ sử dụng PomodoroTimer              |

---

## Backend Integration: NotificationBridge

### 1. Sử Dụng Cơ Bản

```python
from backend.app.services.notification_bridge import NotificationBridge

# Khởi tạo
bridge = NotificationBridge(backend_url="http://localhost:8000")

# Kích hoạt cảnh báo xao nhãng
bridge.trigger_alert(
    alert_type="distraction",
    message="Phát hiện xao nhãng: mất tập trung",
    urgency="high"
)

# Xóa cảnh báo
bridge.clear_alerts(alert_type="distraction")
```

### 2. Tích Hợp Vào Monitoring Router

**File**: `backend/app/routers/monitoring.py`

```python
from fastapi import APIRouter
from backend.app.services.notification_bridge import NotificationBridge

router = APIRouter()
notification_bridge = NotificationBridge(backend_url="http://localhost:8000")

@router.post("/api/detect")
async def detect_from_browser_frame(request: DetectRequest):
    """Detect distraction từ browser frame"""

    # ... existing code ...

    # Phát hiện xao nhãng
    if detect_response.get("distraction") and detect_response.get("is_distracted"):
        # Thông báo lên hệ thống
        notification_bridge.trigger_alert(
            alert_type="distraction",
            message=f"Xao nhãng: {detect_response.get('reason', 'unknown')}",
            urgency="high"
        )

    return detect_response
```

### 3. Hỗ Trợ Nền Tảng

| Nền Tảng | Công Nghệ                       | Cấu Hình                                      |
| -------- | ------------------------------- | --------------------------------------------- |
| Windows  | `plyer` Toast Notification      | Tự động (không cần cấu hình)                  |
| Linux    | `notify-send` + `swaync-client` | Yêu cầu: `sudo apt-get install libnotify-bin` |
| macOS    | `osascript` (AppleScript)       | Tự động (hỗ trợ sẵn)                          |

### 4. Tính Năng Nên Biết

- **Auto-dismiss**: Tự động đóng thông báo desktop sau 5 giây
- **Web Sync**: POST tín hiệu sang `/alert` endpoint để đồng bộ frontend
- **No-duplicate**: Không gửi 2 thông báo cùng loại trong vòng 2 giây
- **Thread-safe**: Sử dụng `threading.Lock()` để tránh race condition

---

## Frontend Integration: useAlertListener + PomodoroTimer

### 1. Hook useAlertListener

**File**: `frontend/src/hooks/useAlertListener.ts`

```typescript
const { isDistracted, alertStatus, lastAlertAt } = useAlertListener({
  sessionId: "session-123",
  pauseTimer: () => console.log("Paused"),
  resumeTimer: () => console.log("Resumed"),
  useWebsocket: true, // Mặc định: Websocket
  debug: false, // Bật logs debug
});
```

#### Return Type

```typescript
interface AlertListenerResult {
  isDistracted: boolean; // Đang bị xao nhãng?
  alertStatus: "idle" | "monitoring" | "error"; // Trạng thái kết nối
  lastAlertAt: Date | null; // Thời gian lần cuối phát hiện xao nhãng
}
```

### 2. Component PomodoroTimer

**File**: `frontend/src/components/PomodoroTimer.tsx`

```typescript
import { PomodoroTimer } from "@/components/PomodoroTimer";

export function MyPage() {
  return (
    <PomodoroTimer
      sessionId="session-123"
      workMinutes={25}
      breakMinutes={5}
    />
  );
}
```

#### Tính Năng

✅ Đồng hồ đếm ngược tự động (25 phút làm việc, 5 phút nghỉ)  
✅ Chỉ báo xao nhãng nhẹ nhàng (chấm nhấp nháy + text)  
✅ Tự động dừng khi AI phát hiện xao nhãng  
✅ Không dùng pop-up, chỉ update UI  
✅ Debug info tích hợp (toggle các button tạm dừng/bỏ qua)

### 3. Trang Demo Page

**File**: `frontend/src/app/pomodoro/page.tsx`

- Tự động lấy hoặc tạo `sessionId`
- Tích hợp thanh điều hướng (Dashboard, Analytics)
- Debug footer với thông tin trạng thái

**Cách sử dụng**:

```bash
# Frontend dev server
cd frontend
npm run dev

# Truy cập: http://localhost:3000/pomodoro
```

---

## Quy Trình Hoạt Động Từ Đầu Đến Cuối

### Bước 1: Khởi Động Backend

```bash
# Terminal 1: Backend
cd backend
python3.10 -m venv .venv310
source .venv310/bin/activate  # Linux/macOS
# \Scripts\activate            # Windows
pip install -r requirements.txt
pip install -r ../frontend/src/features/monitoring/requirements.txt
python main.py
```

**Kiểm tra**:

- ✅ Nhật ký: "Application startup complete"
- ✅ Websocket ready tại `/ws/monitoring`
- ✅ Detect endpoint tại `/api/detect`

### Bước 2: Khởi Động Frontend

```bash
# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

**Kiểm tra**:

- ✅ Application running at http://localhost:3000
- ✅ Pomodoro page accessible tại `/pomodoro`

### Bước 3: Khởi Động Monitoring (AI Pipeline)

```bash
# Terminal 3: Monitoring
cd frontend/src/features/monitoring
source venv/bin/activate  # Venv riêng cho ML models
python main.py
```

**Kiểm tra**:

- ✅ Camera frame capture active
- ✅ detect.debug.log shows latest_age_ms < 10ms
- ✅ Detect service calling backend /api/detect every 300ms

### Bước 4: Mở Pomodoro Page

1. Trình duyệt → http://localhost:3000/pomodoro
2. Cho phép camera access
3. Đặt khuôn mặt vào frame camera
4. Nhấn "▶ Bắt đầu" để bắt đầu đồng hồ

### Bước 5: Test Distraction Detection

1. **Test Tập Trung**: Nhìn vào camera, đồng hồ chạy bình thường, chỉ báo xanh ✅
2. **Test Xao Nhãng**: Quay đầu sang trái/phải, chỉ báo đỏ 🔴, đồng hồ dừng
3. **Test Phục Hồi**: Nhìn lại camera, đồng hồ tiếp tục chạy

**Kỳ Vọng** trong `detect.debug.log`:

```
2024-04-01 10:30:45.123 [INFO] Frame processed | latest_age_ms=2.5 | ai_fps=2.1 | isDistracted=False
2024-04-01 10:30:45.423 [INFO] Frame processed | latest_age_ms=1.8 | ai_fps=2.0 | isDistracted=False
2024-04-01 10:30:45.723 [WARNING] Distraction detected! | face_in_frame=True | head_yaw=45.0deg
2024-04-01 10:30:46.023 [WARNING] Still distracted | head_yaw=52.0deg | is_bad_posture=True
2024-04-01 10:30:46.323 [INFO] Distraction cleared | head_yaw=8.0deg
```

---

## Testing & Debugging

### 1. Kiểm Tra AI Signal Trong Frontend

**DevTools Console**:

```javascript
// Kiểm tra Websocket connection
console.log("Websocket state:", ws.readyState);
// 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED

// Kiểm tra AI signal từ detect response
fetch("/api/detect", {
  method: "POST",
  body: JSON.stringify({ frame: "...", session_id: "debug" }),
})
  .then((r) => r.json())
  .then((d) => console.log("Detect response:", d));
```

### 2. Kiểm Tra Backend Alert

**Backend Logs**:

```python
# Thêm logs vào notification_bridge.py để debug
import logging
logger = logging.getLogger(__name__)

# Xem logs
tail -f /var/log/backend.log | grep "trigger_alert"
```

### 3. Kiểm Tra Database Cache

**SQL Query**:

```sql
-- Kiểm tra intervention state cache
SELECT * FROM intervention_state
WHERE session_id = "session-123"
ORDER BY created_at DESC LIMIT 1;
```

### 4. Kiểm Tra Frontend Hook

**React DevTools**:

```javascript
// Inspect hook state
console.log("Hook state:", {
  isDistracted,
  alertStatus,
  lastAlertAt,
});
```

---

## Troubleshooting

### ❌ Vấn Đề: "No recent AI signal - k khởi động được model"

**Nguyên Nhân**: Backend venv là Python 3.14, monitoring venv là Python 3.10 → ABI mismatch

**Giải Pháp**:

```bash
# Cách 1: Cập nhật backend venv sang Python 3.10
cd backend
python3.10 -m venv .venv310
source .venv310/bin/activate
pip install -r requirements.txt

# Cách 2: Nếu backend yêu cầu Python 3.14, hãy rebuild monitoring venv với 3.14
cd frontend/src/features/monitoring
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ Vấn Đề: "AI not monitoring" - isDistracted = undefined

**Nguyên Nhân**: useAlertListener chưa kết nối được Websocket

**Giải Pháp**:

```javascript
// 1. Kiểm tra Websocket URL trong hook
const wsUrl = useWebsocket ? "ws://localhost:8000/ws/monitoring" : "...";

// 2. Kiểm tra backend Websocket endpoint
# Backend logs
tail -f /var/log/backend.log | grep "ws://"

// 3. Kiểm tra CORS if using HTTP instead of Websocket
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```

### ❌ Vấn Đề: "Distraction detected nhưng timer không dừng"

**Nguyên Nhân**: Hook không ghi được callback `pauseTimer`

**Giải Pháp**:

```typescript
// Kiểm tra callback signature
const pauseTimer = useCallback(() => {
  setIsRunning(false); // Phải là hàm có sideEffect
}, []);

// Truyền đúng vào hook
const { isDistracted } = useAlertListener({
  sessionId,
  pauseTimer, // ✅ Đảm bảo được truyền
  resumeTimer,
  useWebsocket: true,
});

// Kiểm tra hook setup
console.log("pauseTimer provided:", !!pauseTimer);
```

### ❌ Vấn Đề: "PomodoroTimer component không render"

**Nguyên Nhân**: Async sessionId loading

**Giải Pháp**:

```typescript
// Thêm loading state
const [isLoading, setIsLoading] = useState(true);

useEffect(() => {
  // ... fetch sessionId ...
  setIsLoading(false);
}, []);

if (isLoading) return <Skeleton />;
return <PomodoroTimer sessionId={sessionId} />;
```

---

## Cheat Sheet: Các Lệnh Thường Dùng

```bash
# ┌─── Backend ───┐
cd backend
python3.10 -m venv .venv310
source .venv310/bin/activate
pip install -r requirements.txt
python main.py

# ┌─── Frontend ───┐
cd frontend
npm run dev

# ┌─── Monitoring (AI) ───┐
cd frontend/src/features/monitoring
source venv/bin/activate
python main.py

# ┌─── Kiểm tra logs ───┐
tail -f backend.log
tail -f frontend/src/features/monitoring/detect.debug.log

# ┌─── Test Websocket ───┐
wscat -c ws://localhost:8000/ws/monitoring

# ┌─── Test Detect API ───┐
curl -X POST http://localhost:8000/api/detect \
  -H "Content-Type: application/json" \
  -d '{"frame": "...", "session_id": "test"}'
```

---

## Tham Khảo Thêm

- [useAlertListener Hook Documentation](../hooks/useAlertListener.ts)
- [NotificationBridge Class Documentation](../../app/services/notification_bridge.py)
- [PomodoroTimer Component Documentation](./PomodoroTimer.tsx)
- [Backend Detect Service](../../app/services/browser_detect_service.py)
- [Monitoring Config](./config/performance_config.py)

---

**Tác giả**: GitHub Copilot  
**Ngày Cập Nhật**: 2024-04-01  
**Trạng Thái**: ✅ Production Ready
