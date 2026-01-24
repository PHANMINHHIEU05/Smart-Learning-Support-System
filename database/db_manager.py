import sqlite3
import os
from datetime import datetime
from typing import List, Tuple, Optional
import logging
from database.models import (
    CREATE_TABLE_SESSIONS,
     CREATE_INDEXES,
     INSERT_SESSION,
)
class DatabaseManager:
     """
     Class quản lý SQLite database cho hệ thống 
     Attributes:
          db_path (str): đường dẫn tới file database
          conn (sqlite3.Connection): kết nối database
          cursor (sqlite3.Cursor): con trỏ database
     """
     def __init__(self, db_path: str = "data/study_behavior.db"):
          self.db_path = db_path
          self.conn = None
          self.cursor = None
          self._ensure_db_directory()
     def _ensure_db_directory(self):
          """đảm bảo thư mục data base tồn tại"""
          dir_path = os.path.dirname(self.db_path)
          if dir_path and not os.path.exists(dir_path):
               os.makedirs(dir_path)
     def connect(self):
          """kết nối đến database 
          nếu file chưa được tạo thì tạo mới """
          try:
               self.conn = sqlite3.connect(self.db_path , check_same_thread=False)
               self.cursor = self.conn.cursor()
               print(f"✅ Kết nối database thành công: {self.db_path}")
          except sqlite3.Error as e:
               print(f"❌ Lỗi kết nối database: {e}")
               raise
     def create_tables(self):
          """tạo bảng và index nếu chưa tồn tại """
          try:
               self.cursor.execute(CREATE_TABLE_SESSIONS)
               for index_query in CREATE_INDEXES:
                    self.cursor.execute(index_query)
               self.conn.commit()
          except sqlite3.Error as e:
               print(f"❌ Lỗi tạo bảng hoặc index: {e}")
               raise
     def insert_record(self, data: Tuple):
          try:
               self.cursor.execute(INSERT_SESSION, data)
               self.conn.commit()
               return self.cursor.lastrowid
          except sqlite3.Error as e:
               print(f"❌ Lỗi chèn bản ghi: {e}")
               return  None
     def  insert_batch(self, data_list: List[Tuple]):
          """insert nhiều bản ghi cùng lúc"""
          try:
               self.cursor.executemany(INSERT_SESSION, data_list)
               self.conn.commit()
               return len(
                    data_list
               )
          except sqlite3.Error as e:
               print(f"❌ Lỗi chèn bản ghi hàng loạt: {e}")
               return 0
     def get_avg_focus_score(self, hours: int = 1) -> Optional[float]:
        """
        Lấy điểm focus trung bình trong X giờ qua
        
        Args:
            hours: Số giờ cần tính (mặc định 1)
        
        Returns:
            float: Điểm trung bình, hoặc None nếu không có dữ liệu
        """
        query = f"""
        SELECT AVG(focus_score) 
        FROM study_sessions
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
        """
        Lấy thống kê của 1 session
        
        Args:
            session_id: ID của session
        
        Returns:
            dict: Thống kê (avg_focus, drowsy_count, duration...)
        """
        stats = {}
        
        # Điểm trung bình
        query_avg = """
        SELECT AVG(focus_score), COUNT(*) 
        FROM study_sessions 
        WHERE session_id = ?;
        """
        self.cursor.execute(query_avg, (session_id,))
        avg, count = self.cursor.fetchone()
        stats['avg_focus_score'] = round(avg, 2) if avg else 0
        stats['total_records'] = count
        
        # Số lần cảnh báo
        query_warnings = """
        SELECT 
            SUM(is_drowsy) as drowsy_count,
            SUM(is_bad_posture) as posture_count
        FROM study_sessions
        WHERE session_id = ?;
        """
        self.cursor.execute(query_warnings, (session_id,))
        drowsy, posture = self.cursor.fetchone()
        stats['drowsy_warnings'] = drowsy or 0
        stats['posture_warnings'] = posture or 0
        
        return stats
    
     def close(self):
        """Đóng kết nối database"""
        if self.conn:
            self.conn.close()
            print("✅ Đã đóng kết nối database")