# bộ lọc moving average để làm mượt dữ liệu loại bỏ nhiễu 
from collections import deque
from typing import List, Optional
class MovingAverageFilter:
     """
     Docstring for MovingAverageFilter
     bộ lọc moving average để làm mượt dữ liệu loại bỏ nhiễu
     hỗ trợ 2 phương pháp:
     1. simple moving average (SMA): trung bình đơn giản 
     2. EMA (exponential moving average): trung bình hàm mũ
     """
     def __init__(self, window_size: int = 7, method: str = 'ema'):
          """
          Khởi tạo bộ lọc
          
          Args:
               window_size (int): kích thước cửa sổ frame
               method (str): phương pháp lọc ('sma' hoặc 'ema')
          """
          self.window_size = window_size
          self.method = method.lower()
          self.buffer: deque =  deque(maxlen=window_size)
          self.ema_value: Optional[float] = None
          self.alpha = 2 / (window_size + 1)  # hệ số làm mượt cho EMA
          self.sample_count = 0
     def reset(self):
          """đặt lại bộ lọc"""
          self.buffer.clear()
          self.ema_value = None
          self.sample_count = 0
     def uppdate(self, value: float) -> float:
          """thêm giá trị mới và giá trị đã làm mượt"""
          self.sample_count += 1
          if self.method == 'sma':
               return self._update_sma(value)
          elif self.method == 'ema':
               return self._update_ema(value)
     def _update_sma(self, value: float) -> float:
          """cập nhật và trả về giá trị SMA"""
          self.buffer.append(value)
          sma = sum(self.buffer) / len(self.buffer)
          return sma
     def _update_ema(self, value: float) -> float:
          """cập nhật và trả về giá trị EMA"""
          if self.ema_value is None:
               self.ema_value = value
          else:
            self.ema_value = self.alpha * value + (1 - self.alpha) * self.ema_value
          return self.ema_value
     def get_current_value(self) -> Optional[float]:
          """lấy giá trị đã làm mượt hiện tại """
          if self.method == 'sma':
               if len(self.buffer) == 0:
                    return None
               return sum(self.buffer)/ len(self.buffer)
          else:
               return self.ema_value
     def is_ready(self) -> bool:
          """ kiểm tra bộ lọc dữ liệu đã đủ chưa 
               với SMA : cần đủ window_size sample 
               với EMA : chỉ cần 1 sample      
          """
          if self.method == 'sma':
               return len(self.buffer) >= self.window_size
          else:
               return self.ema_value is not None
     def get_buffer_values(self) -> List[float]:
          return list(self.buffer)
class MultiChannelFilter:
     """bộ lọc cho nhiều kênh  1 lúc """
     """ ví dụ như lóc đồng thời ear , head tilt , shoulder_angle"""
     def __init__(self, channels: List[str], window_size: int = 7, method: str = 'ema'):
          self.channels = channels
          self.filters = {
               channel: MovingAverageFilter(window_size, method)
               for channel in channels
          }
     def reset(self):
          """đặt lại tất cả bộ lọc"""
          for filter in self.filters.values():
               filter.reset()
     def update(self, values: dict) -> dict:
          smoothed = {}
          for channel, value in values.items():
               if channel in self.filters:
                    smoothed[channel] = self.filters[channel].uppdate(value)
               else:
                    smoothed[channel] = value  # không lọc nếu kênh không tồn tại
          return smoothed
     def get_filter(self, channel: str) -> Optional[MovingAverageFilter]:
          return self.filters.get(channel, None)
