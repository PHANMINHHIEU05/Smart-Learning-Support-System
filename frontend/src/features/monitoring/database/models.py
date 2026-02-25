# SQL Schema cho database

CREATE_TABLE_SESSIONS = """
CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Dữ liệu mắt
    ear_left REAL,
    ear_right REAL,
    ear_avg REAL,
    
    -- Dữ liệu tư thế
    head_tilt_angle REAL,
    shoulder_slope REAL,
    distance_to_screen REAL,
    posture_score REAL,
    
    -- Biểu cảm
    emotion TEXT,
    emotion_confidence REAL,
    
    -- Điểm tổng hợp
    focus_score REAL,

    -- Trạng thái cảnh báo
    is_drowsy INTEGER DEFAULT 0,
    is_bad_posture INTEGER DEFAULT 0,
    
    -- Metadata
    notes TEXT,
    session_id TEXT
)
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_timestamp ON study_sessions(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_focus_score ON study_sessions(focus_score);",
    "CREATE INDEX IF NOT EXISTS idx_session_id ON study_sessions(session_id);",
]

INSERT_SESSION = """
INSERT INTO study_sessions (
    ear_left, ear_right, ear_avg,
    head_tilt_angle, shoulder_slope, distance_to_screen, posture_score,
    emotion, emotion_confidence, focus_score,
    is_drowsy, is_bad_posture, session_id
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
"""

