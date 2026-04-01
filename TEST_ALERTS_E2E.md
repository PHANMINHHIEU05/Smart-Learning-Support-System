# End-to-End Alert System Test Guide

## Overview

This guide walks through validating that the complete alert pipeline works:

1. Default alert rules seed automatically for new user sessions
2. Detect API generates rich AI events (drowsiness, posture, distance)
3. Alert rules match and fire alerts
4. Alerts stream to frontend via WebSocket
5. Frontend displays alerts as visual badges

---

## Prerequisites

### Terminal 1: Backend Server

```bash
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System
source .venv310/bin/activate
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Database Check (Optional)

```bash
# After server starts, verify alert rules were created for your user
psql $DATABASE_URL -c "SELECT user_id, name, trigger_event_type FROM alert_rules LIMIT 10;"
```

### Terminal 3: Frontend (if testing UI)

```bash
cd /home/hiubeo/Documents/code/Smart-Learning-Support-System/frontend
npm run dev
# Opens http://localhost:3000
```

---

## Test Scenario 1: Verify Default Rules Are Seeded

### Step 1a: Start a monitoring session

```bash
curl -X POST http://localhost:8000/api/v1/monitoring/start \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session-001", "show_display": false}'
```

### Expected Response

```json
{
  "status": "active",
  "active_mode": "browser_camera",
  "pid": 12345,
  "severity_defaults": {
    "critical": ["..."],
    "medium": ["..."],
    "soft": ["..."]
  }
}
```

### Step 1b: Check that default rules exist in DB

```bash
psql $DATABASE_URL -c "
SELECT COUNT(*) as rule_count FROM alert_rules WHERE user_id = 'YOUR_USER_ID' AND is_enabled = true;
"
```

**Expected**: Should show 6 or more default rules (one per detection type).

---

## Test Scenario 2: Send a Frame to `/detect` and Verify Event

### Step 2a: Create a test image (all black for simplicity)

```bash
python3 << 'PY'
import cv2
import numpy as np

# Create a 360×640 black frame
black_frame = np.zeros((360, 640, 3), dtype=np.uint8)
ok, encoded = cv2.imencode('.jpg', black_frame)
with open('/tmp/test_frame.jpg', 'wb') as f:
    f.write(encoded.tobytes())
print("Saved /tmp/test_frame.jpg")
PY
```

### Step 2b: Send frame to detect endpoint

```bash
curl -X POST http://localhost:8000/api/v1/monitoring/detect \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "frame=@/tmp/test_frame.jpg" \
  -F "session_id=test-session-001" \
  -F "client_ts_ms=$(date +%s)000" \
  -F "frame_seq=1" \
  2>/dev/null | jq .
```

### Expected Response

```json
{
  "ready": true,
  "focus_score": 0.0,
  "confidence": 0.0,
  "state_flags": {
    "is_drowsy": false,
    "is_bad_posture": false,
    "is_distracted": false,
    "is_using_phone": false,
    "is_too_close": false,
    "is_too_far": false
  },
  "derived_event": "focus_update",
  "overlay": {
    "labels": [
      {
        "text": "focus: 0.0",
        "x": 18,
        "y": 28,
        "severity": "soft"
      }
    ]
  },
  ...
}
```

**Key observations**:

- `ready: true` means AI model initialized in backend
- `derived_event` shows what type of event was detected
- `state_flags` includes new `is_too_close` and `is_too_far` fields
- `overlay.labels` include warning text for abnormal states

---

## Test Scenario 3: Verify Alert Event Was Created and Fired

### Step 3a: Query recent alert events

```bash
psql $DATABASE_URL -c "
SELECT
  event_id,
  event_type,
  severity,
  confidence,
  created_at
FROM ai_events
WHERE session_id = '3e8e8c1c-...'
  AND created_at > NOW() - INTERVAL '5 minutes'
ORDER BY created_at DESC
LIMIT 5;
"
```

**Expected**: Should see rows with event_type = 'focus_update' or other derived events.

### Step 3b: Query recent alerts triggered by rules

```bash
psql $DATABASE_URL -c "
SELECT
  a.alert_id,
  ar.name as rule_name,
  a.message,
  a.payload_json->'severity' as severity,
  a.fired_at
FROM alerts a
LEFT JOIN alert_rules ar ON a.rule_id = ar.rule_id
WHERE a.session_id = '3e8e8c1c-...'
  AND a.fired_at > NOW() - INTERVAL '5 minutes'
ORDER BY a.fired_at DESC
LIMIT 5;
"
```

**Expected**: If AI detected abnormal states, you'd see alerts with:

- `rule_name`: e.g., "Drowsiness Warning", "Too Close To Screen"
- `severity`: "critical", "medium", or "soft"
- `payload_json`: includes `event_type`, `confidence`, `rule_name`

---

## Test Scenario 4: Test WebSocket Alerts Stream (Frontend Integration)

### Step 4a: Get a stream ticket

```bash
TICKET=$(curl -s -X POST http://localhost:8000/api/v1/monitoring/stream-ticket \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" | jq -r .ticket)
echo "Ticket: $TICKET"
```

### Step 4b: Listen on alerts-stream WebSocket

Using a WebSocket client (e.g., `websocat` or browser console):

```bash
websocat "ws://localhost:8000/api/v1/monitoring/alerts-stream?ticket=$TICKET&session_id=test-session-001"
```

Or in browser Console:

```javascript
const ticket = "..."; // from 4a
const sessionId = "test-session-001";
const ws = new WebSocket(
  `ws://localhost:8000/api/v1/monitoring/alerts-stream?ticket=${ticket}&session_id=${sessionId}`,
);
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  console.log("Alert received:", msg);
};
```

### Step 4c: Trigger an alert (send multiple frames)

```bash
for i in {1..3}; do
  curl -s -X POST http://localhost:8000/api/v1/monitoring/detect \
    -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    -F "frame=@/tmp/test_frame.jpg" \
    -F "session_id=test-session-001" \
    -F "client_ts_ms=$(date +%s)000" \
    -F "frame_seq=$i" > /dev/null
  sleep 1.5  # Throttle to allow 1 event per second
done
```

### Expected WebSocket Message

```json
{
  "type": "alert",
  "session_id": "test-session-001",
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "severity": "medium",
  "event_type": "focus_offscreen",
  "message": "[Distraction Warning] Phát hiện: focus_offscreen",
  "created_at": "2026-03-25T12:34:56Z"
}
```

**Key fields**:

- `severity`: one of critical, medium, soft
- `event_type`: what was detected (drowsiness, bad_posture, etc.)
- `message`: human-readable alert text

---

## Test Scenario 5: Frontend Alert Badge Display

### Prerequisites

- Frontend running on http://localhost:3000
- User logged in
- Navigate to Timer page with active session

### Steps

1. Open the browser DevTools (F12) and check Console
2. Click **Start Camera** in CameraWidget
3. Watch for frames being sent to `/detect` endpoint every 500ms
4. If AI detects anomalies, look for:
   - **Overlay warnings** on the video canvas (text labels)
   - **Toast badges** in bottom-right corner (colored alerts)
   - **Console logs** showing alert-stream messages

### Expected UI Behavior

- **Critical alerts** (e.g., phone detected, drowsiness) → Red badge, 5s visible
- **Medium alerts** (e.g., bad posture, too close) → Orange badge, 3s visible
- **Soft alerts** (e.g., focus low) → Blue badge, 2s visible

Each badge shows:

- Rule name (e.g., "Drowsiness Warning")
- Event type (e.g., "drowsiness")
- Timestamp

---

## Troubleshooting

### Issue: No alerts appearing in WebSocket

**Diagnosis**:

1. Check that default rules were created:
   ```bash
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM alert_rules WHERE user_id = 'YOUR_USER_ID';"
   ```
2. Check that ai_events are being created:
   ```bash
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM ai_events WHERE session_id = '...' AND created_at > NOW() - INTERVAL '1 minute';"
   ```
3. Check alert firing logs in backend server output

### Issue: AI model not initializing (ready=false)

1. Ensure backend is running in Python 3.10 venv:
   ```bash
   source .venv310/bin/activate
   python --version  # Should be 3.10.x
   ```
2. Check that monitoring venv exists:
   ```bash
   ls -la frontend/src/features/monitoring/venv/bin/python
   ```

### Issue: Frontend doesn't show AlertBadge

1. Verify AlertBadge.tsx exists:
   ```bash
   ls -la frontend/src/components/AlertBadge.tsx
   ```
2. Check browser Console for import errors
3. Ensure CameraWidget is passing `alerts` prop correctly

---

## Success Criteria

✅ Default rules are seeded (6 rules created per user)  
✅ Detect API returns rich state_flags (is_too_close, is_too_far, etc.)  
✅ Overlay text shows multiple warnings (not just focus score)  
✅ Alerts are created in DB when events match rules  
✅ WebSocket alerts-stream sends alert messages with correct severity  
✅ Frontend displays alerts as visual badges with color-coded severity

---

## Performance Notes

- Detect API throttles event creation to 1 event/second per user (via `_DETECT_EVENT_THROTTLE_SEC`)
- Alert cooldowns prevent spam (20s min between same rule alerts)
- WebSocket polls DB every 0.8s for new alerts
- Frontend keeps up to 10 alerts in memory and displays top 3
