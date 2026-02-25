import sqlite3
import os
from typing import List, Tuple, Optional
from database.models import CREATE_TABLE_SESSIONS, CREATE_INDEXES, INSERT_SESSION


class DatabaseManager:
    """Quản lý SQLite database cho hệ thống"""
    
    def __init__(self, db_path: str = "data/study_behavior.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._ensure_db_directory()

    def _ensure_db_directory(self):
        dir_path = os.path.dirname(self.db_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            print(f"✅ Kết nối database: {self.db_path}")
        except sqlite3.Error as e:
            print(f"❌ Lỗi kết nối database: {e}")
            raise

    def create_tables(self):
        try:
            self.cursor.execute(CREATE_TABLE_SESSIONS)
            for idx in CREATE_INDEXES:
                self.cursor.execute(idx)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"❌ Lỗi tạo bảng: {e}")
            raise

    def insert_record(self, data: Tuple) -> Optional[int]:
        try:
            self.cursor.execute(INSERT_SESSION, data)
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"❌ Lỗi insert: {e}")
            return None

    def insert_batch(self, data_list: List[Tuple]) -> int:
        try:
            self.cursor.executemany(INSERT_SESSION, data_list)
            self.conn.commit()
            return len(data_list)
        except sqlite3.Error as e:
            print(f"❌ Lỗi batch insert: {e}")
            return 0

    def get_avg_focus_score(self, hours: int = 1) -> Optional[float]:
        query = f"""
        SELECT AVG(focus_score) FROM study_sessions
        WHERE timestamp > datetime('now', '-{hours} hours');
        """
        try:
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            return result[0] if result[0] else None
        except sqlite3.Error as e:
            print(f"❌ Lỗi query: {e}")
            return None

    def get_session_stats(self, session_id: str) -> dict:
        query = """
        SELECT 
            AVG(focus_score) as avg_focus,
            SUM(is_drowsy) as drowsy_count,
            SUM(is_bad_posture) as bad_posture_count,
            COUNT(*) as total_records
        FROM study_sessions WHERE session_id = ?;
        """
        try:
            self.cursor.execute(query, (session_id,))
            row = self.cursor.fetchone()
            return {
                'avg_focus': row[0],
                'drowsy_count': row[1],
                'bad_posture_count': row[2],
                'total_records': row[3]
            }
        except sqlite3.Error as e:
            print(f"❌ Lỗi query: {e}")
            return {}

    def close(self):
        if self.conn:
            self.conn.close()
            print("✅ Đã đóng kết nối database")
