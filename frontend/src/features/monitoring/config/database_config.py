TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ear_value REAL,
    ear_left REAL,
    ear_right REAL,
    posture_score REAL,
    head_tilt_angle REAL,
    distance_to_screen REAL,
    emotion TEXT,
    emotion_confidence REAL,
    focus_score REAL,
    warning_drowsy INTEGER,
    warning_posture INTEGER
);
"""

# Index để tăng tốc query
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_timestamp ON study_sessions(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_focus_score ON study_sessions(focus_score);",
]