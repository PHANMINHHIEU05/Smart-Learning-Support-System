from collections import deque
from typing import List, Optional, Dict


class MovingAverageFilter:
    """Bộ lọc Moving Average để làm mượt dữ liệu
    
    Hỗ trợ:
    - SMA (Simple Moving Average): Trung bình đơn giản
    - EMA (Exponential Moving Average): Trung bình hàm mũ, phản ứng nhanh hơn
    """
    
    def __init__(self, window_size: int = 7, method: str = 'ema'):
        self.window_size = window_size
        self.method = method.lower()
        self.buffer: deque = deque(maxlen=window_size)
        self.ema_value: Optional[float] = None
        self.alpha = 2 / (window_size + 1)  # Hệ số EMA
        self.sample_count = 0

    def reset(self):
        self.buffer.clear()
        self.ema_value = None
        self.sample_count = 0

    def update(self, value: float) -> float:
        """Thêm giá trị mới và trả về giá trị đã làm mượt"""
        self.sample_count += 1
        if self.method == 'sma':
            return self._update_sma(value)
        return self._update_ema(value)

    def _update_sma(self, value: float) -> float:
        self.buffer.append(value)
        return sum(self.buffer) / len(self.buffer)

    def _update_ema(self, value: float) -> float:
        """EMA = α * value + (1 - α) * EMA_prev"""
        if self.ema_value is None:
            self.ema_value = value
        else:
            self.ema_value = self.alpha * value + (1 - self.alpha) * self.ema_value
        return self.ema_value

    def get_current_value(self) -> Optional[float]:
        if self.method == 'sma':
            return sum(self.buffer) / len(self.buffer) if self.buffer else None
        return self.ema_value

    def is_ready(self) -> bool:
        if self.method == 'sma':
            return len(self.buffer) >= self.window_size
        return self.ema_value is not None


class MultiChannelFilter:
    """Bộ lọc cho nhiều kênh đồng thời (ear, head_tilt, etc.)"""
    
    def __init__(self, channels: List[str], window_size: int = 7, method: str = 'ema'):
        self.channels = channels
        self.filters = {ch: MovingAverageFilter(window_size, method) for ch in channels}

    def reset(self):
        for f in self.filters.values():
            f.reset()

    def update(self, values: Dict[str, float]) -> Dict[str, float]:
        """Cập nhật tất cả kênh và trả về giá trị đã làm mượt"""
        smoothed = {}
        for channel, value in values.items():
            if channel in self.filters:
                smoothed[channel] = self.filters[channel].update(value)
            else:
                smoothed[channel] = value
        return smoothed

    def get_filter(self, channel: str) -> Optional[MovingAverageFilter]:
        return self.filters.get(channel)
