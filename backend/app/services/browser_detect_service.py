from __future__ import annotations
from asyncio import Queue
import sys 
import time 
from pathlib import Path


_MONITORING_ROOT = {
    Path(__file__).resolve().parents[3] 
    /"frontend"
    /"src"
    /"features"
    /"monitoring"
}
if str(_MONITORING_ROOT) not in sys.path:
    sys.path.append(str(_MONITORING_ROOT))
from core.ai_processor import AIProcessorThread # type: ignore
class BrowserDetectService:
    """phân tích frame upload tu browser va tra JSON metrics """
    def __init__(self) -> None:
        self._frame_queue = Queue(maxsize=2)
        