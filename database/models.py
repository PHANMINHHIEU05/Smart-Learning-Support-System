CREATE_TABLE_SESSIONS = """
CREATE TABLE IF NOT EXISTS study_sessions (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
     -- dữ liệu mắt 
     ear_left REAL,
     ear_right REAL,
     ear_avg REAL,
     -- dữ liệu tư thế 
     head_tilt_angle REAL,
     shoulder_slope REAL,
     distance_to_screen REAL,
     posture_score REAL,
     -- dữ liệu biểu cảm khuôn mặt
     emotion TEXT,
     emotion_confidence REAL,
     -- điểm tổng hợp 
     focus_score REAL,

     -- trạng thái cảnh báo
     is_drowsy INTEGER DEFAULT 0,
     is_bad_posture INTEGER DEFAULT 0,
     -- metadata khác
     notes TEXT,
     session_id TEXT
)
"""

# indexs tăng tốc query 
CREATE_INDEXES = [
    """CREATE INDEX IF NOT EXISTS idx_timestamp 
       ON study_sessions(timestamp);""",
    
    """CREATE INDEX IF NOT EXISTS idx_focus_score 
       ON study_sessions(focus_score);""",
    
    """CREATE INDEX IF NOT EXISTS idx_session_id 
       ON study_sessions(session_id);""",
]

# query thường dùng 
# Insert 1 record vào bảng sessions
INSERT_SESSION = """
INSERT INTO study_sessions (
     ear_left, ear_right, ear_avg,
     head_tilt_angle, shoulder_slope, distance_to_screen,
     posture_score,
     emotion, emotion_confidence,
     focus_score,
     is_drowsy, is_bad_posture,
     session_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
"""
# Lấy điểm trung bình qua 1 giờ qua 
GET_AVG_FOCUS_LAST_HOUR = """
SELECT AVG(focus_score) as avg_focus
FROM study_sessions
WHERE timestamp >= datetime('now', '-1 hour');
"""

