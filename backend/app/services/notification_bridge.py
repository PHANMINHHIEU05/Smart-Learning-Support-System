"""
NotificationBridge: Xử lý cảnh báo xao nhãng đa nền tảng (Windows/Linux).

Tính năng:
- Windows: Dùng thư viện plyer để hiện Toast notification
- Linux: Dùng lệnh notify-send với mức độ critical
- Linux/SwayNC: Thi hành swaync-client -cl để xóa cảnh báo khi người dùng tập trung trở lại
- Web sync: Gửi POST request đến FastAPI backend để đồng bộ trạng thái
- Tối ưu: Không gửi cảnh báo trùng lặp nếu trạng thái không thay đổi

Hỗ trợ: Windows, Linux (Fedora/Hyprland/SwayNC), macOS (notify-send)
"""

import logging
import platform
import subprocess
import threading
import time
from typing import Optional

import requests

logger = logging.getLogger("app.notification_bridge")


class NotificationBridge:
    """
    Bộ cầu nối thông báo xao nhãng với hỗ trợ đa nền tảng.
    
    Ví dụ:
        bridge = NotificationBridge(backend_url="http://localhost:8000")
        bridge.trigger_alert("Bạn đang xao nhãng!")
        # ... người dùng tập trung trở lại
        bridge.clear_alerts()
    """

    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        request_timeout: float = 5.0,
        enable_backend_sync: bool = False,
    ):
        """
        Khởi tạo NotificationBridge.
        
        Args:
            backend_url: URL gốc của FastAPI backend (mặc định: http://localhost:8000)
            request_timeout: Timeout cho HTTP request (mặc định: 5 giây)
        """
        self.backend_url = backend_url
        self.request_timeout = request_timeout
        self.enable_backend_sync = enable_backend_sync
        
        # Nhận diện hệ điều hành
        self.system = platform.system()  # "Windows", "Linux", "Darwin" (macOS)
        
        # Cờ để tránh gửi cảnh báo trùng lặp
        self._is_alerting = False
        
        # Lock cho thread-safe operations
        self._lock = threading.Lock()
        
        logger.info("NotificationBridge initialized on %s", self.system)

    def trigger_alert(self, message: str, severity: str = "critical") -> None:
        """
        Phát đi thông báo xao nhãng ngay lập tức.
        
        Tối ưu: Chỉ gửi nếu trạng thái từ bình thường → xao nhãng (tránh trùng lặp).
        
        Args:
            message: Nội dung thông báo (ví dụ: "Bạn đang xao nhãng!")
            severity: Mức độ ("critical", "warning", "info"); mặc định là "critical"
        """
        with self._lock:
            # Nếu đã đang gửi cảnh báo, không gửi lại (tránh spam)
            if self._is_alerting:
                logger.debug("Alert already active, skipping duplicate trigger")
                return
            
            self._is_alerting = True
        
        logger.info("Triggering alert: %s (severity=%s)", message, severity)
        
        # Gửi thông báo hệ thống dựa trên nền tảng
        self._show_system_notification(message, severity)
        
        # Optional backend sync (disabled by default because /alert endpoint is absent).
        if self.enable_backend_sync:
            threading.Thread(
                target=self.sync_to_backend,
                args=("start",),
                daemon=True,
            ).start()

    def clear_alerts(self) -> None:
        """
        Xóa/tắt tất cả cảnh báo xao nhãng.
        
        - Windows: Cảnh báo tự điểm sau timeout.
        - Linux: Dùng swaync-client -cl (SwayNC) hoặc notification daemon cấp độ hệ thống.
        
        Gọi phương thức này khi người dùng tập trung trở lại.
        """
        with self._lock:
            if not self._is_alerting:
                logger.debug("No alerts active, skipping clear")
                return
            
            self._is_alerting = False
        
        logger.info("Clearing all alerts")
        
        # Xóa thông báo dựa trên hệ điều hành
        if self.system == "Linux":
            self._clear_linux_notifications()
        elif self.system == "Windows":
            # Windows Toast sẽ tự điểm sau 1-2 phút
            logger.debug("Windows notifications dismiss automatically")
        elif self.system == "Darwin":
            # macOS notification center
            logger.debug("macOS notifications handled by system")
        
        # Optional backend sync (disabled by default because /alert endpoint is absent).
        if self.enable_backend_sync:
            threading.Thread(
                target=self.sync_to_backend,
                args=("stop",),
                daemon=True,
            ).start()

    def sync_to_backend(self, status: str) -> None:
        """
        Gửi POST request đến FastAPI backend để đồng bộ trạng thái cảnh báo.
        
        Endpoint: http://localhost:8000/alert
        Payload:  {"status": "start"|"stop", "timestamp": <unixtime>}
        
        Args:
            status: "start" = cảnh báo bắt đầu, "stop" = cảnh báo kết thúc
        """
        if status not in ("start", "stop"):
            logger.warning("Invalid status: %s", status)
            return
        
        payload = {
            "status": status,
            "timestamp": int(time.time()),
        }
        
        try:
            response = requests.post(
                f"{self.backend_url}/alert",
                json=payload,
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            logger.debug("Backend sync OK: status=%s", status)
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to sync with backend: %s", e)

    def _show_system_notification(self, message: str, severity: str) -> None:
        """
        Hiển thị thông báo hệ thống dựa vào nền tảng.
        
        Args:
            message: Nội dung thông báo
            severity: Mức độ ("critical", "warning", "info")
        """
        if self.system == "Windows":
            self._show_windows_notification(message, severity)
        elif self.system == "Linux":
            self._show_linux_notification(message, severity)
        elif self.system == "Darwin":
            self._show_macos_notification(message, severity)
        else:
            logger.warning("Unsupported system: %s", self.system)

    def _show_windows_notification(self, message: str, severity: str) -> None:
        """
        Hiển thị Toast notification trên Windows dùng plyer.
        
        Yêu cầu: pip install plyer
        
        Args:
            message: Nội dung thông báo
            severity: Mức độ (plyer sẽ bỏ qua, Windows tự quyết định icon)
        """
        try:
            from plyer import notification
            
            # Tiêu đề dựa trên mức độ
            title = {
                "critical": "🚨 Cảnh báo: Xao nhãng!",
                "warning": "⚠️ Cảnh báo",
                "info": "ℹ️ Thông tin",
            }.get(severity, "Thông báo")
            
            notification.notify(
                title=title,
                message=message,
                timeout=30,  # Hiển thị 30 giây
                app_name="Smart Learning Support System",
            )
            logger.info("Windows notification shown: %s", title)
        except ImportError:
            logger.warning("plyer not installed. Install with: pip install plyer")
        except Exception as e:
            logger.error("Failed to show Windows notification: %s", e)

    def _show_linux_notification(self, message: str, severity: str) -> None:
        """
        Hiển thị thông báo trên Linux dùng notify-send.
        
        Hỗ trợ: Fedora, Ubuntu, Debian, và các hệ thống có notify-send.
        Đặc biệt hỗ trợ SwayNC (Hyprland notification center).
        
        Yêu cầu: sudo dnf install libnotify (Fedora) hoặc apt install libnotify-bin
        
        Args:
            message: Nội dung thông báo
            severity: Mức độ ("critical", "warning", "info")
        """
        try:
            # Xác định urgency dựa vào severity
            urgency = {
                "critical": "critical",
                "warning": "normal",
                "info": "low",
            }.get(severity, "normal")
            
            # Tiêu đề dựa trên mức độ
            title = {
                "critical": "🚨 Cảnh báo: Xao nhãng!",
                "warning": "⚠️ Cảnh báo",
                "info": "ℹ️ Thông tin",
            }.get(severity, "Thông báo")
            
            # Gọi notify-send với cờ phù hợp
            cmd = [
                "notify-send",
                "-u", urgency,  # urgency: low, normal, critical
                "-t", "30000",  # timeout: 30 giây (ms)
                "-a", "Smart-Learning",  # app name
                title,
                message,
            ]
            
            subprocess.run(cmd, check=False, timeout=5)
            logger.info("Linux notification shown via notify-send")
        except FileNotFoundError:
            logger.warning(
                "notify-send not found. Install with: "
                "sudo dnf install libnotify (Fedora) or sudo apt install libnotify-bin (Ubuntu)"
            )
        except Exception as e:
            logger.error("Failed to show Linux notification: %s", e)

    def _show_macos_notification(self, message: str, severity: str) -> None:
        """
        Hiển thị thông báo trên macOS dùng osascript.
        
        Args:
            message: Nội dung thông báo
            severity: Mức độ (macOS sẽ bỏ qua, sử dụng notification center)
        """
        try:
            title = {
                "critical": "🚨 Cảnh báo: Xao nhãng!",
                "warning": "⚠️ Cảnh báo",
                "info": "ℹ️ Thông tin",
            }.get(severity, "Thông báo")
            
            script = f'display notification "{message}" with title "{title}"'
            cmd = ["osascript", "-e", script]
            
            subprocess.run(cmd, check=False, timeout=5)
            logger.info("macOS notification shown")
        except Exception as e:
            logger.error("Failed to show macOS notification: %s", e)

    def _clear_linux_notifications(self) -> None:
        """
        Xóa tất cả thông báo trên Linux.
        
        Ưu tiên:
        1. swaync-client -C (SwayNC, đặc biệt hỗ trợ Hyprland)
        2. Fallback cho systemd user timers hoặc notification daemon khác
        
        Ghi chú cho Fedora Hyprland:
        - SwayNC là mặc định; nó lưu thông báo trong một tray/center
        - Lệnh swaync-client -C sẽ xóa sạch tất cả thông báo ngay lập tức
        """
        logger.debug("Clearing Linux notifications")
        
        # Thử xóa dùng swaync-client (SwayNC)
        try:
            cmd = ["swaync-client", "-C"]
            subprocess.run(cmd, check=False, timeout=5)
            logger.info("Notifications cleared via swaync-client")
            return
        except FileNotFoundError:
            logger.debug("swaync-client not found, trying alternative methods")
        except Exception as e:
            logger.warning("swaync-client failed: %s", e)
        
        # Fallback: Thử dùng notify-send để gửi thông báo "close" (nếu được hỗ trợ)
        # Ghi chú: Điều này không hiệu quả 100% trên tất cả DM, nhưng là cách tốt nhất
        try:
            # Một số notification daemon hỗ trợ D-Bus API, nhưng notify-send không cung cấp lệnh đóng trực tiếp
            # Do đó, chúng tôi sẽ log rằng notification daemon cần xóa thông báo theo cách khác
            logger.info("Notifications will be auto-dismissed by notification daemon")
        except Exception as e:
            logger.warning("Failed to clear notifications: %s", e)

    def is_active(self) -> bool:
        """
        Kiểm tra xem có cảnh báo đang hoạt động không.
        
        Returns:
            True nếu đang gửi cảnh báo, False nếu không.
        """
        with self._lock:
            return self._is_alerting


# ============================================================================
# Ví dụ sử dụng
# ============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    
    # Khởi tạo bridge
    bridge = NotificationBridge()
    
    print("Testing NotificationBridge...")
    print(f"System: {bridge.system}")
    print()
    
    # Gửi cảnh báo
    print("[1/3] Triggering distraction alert...")
    bridge.trigger_alert("Bạn đang xao nhãng! Hãy tập trung vào màn hình.")
    time.sleep(2)
    
    # Kiểm tra trạng thái
    print(f"[2/3] Is alerting: {bridge.is_active()}")
    time.sleep(2)
    
    # Xóa cảnh báo
    print("[3/3] Clearing alerts...")
    bridge.clear_alerts()
    time.sleep(1)
    
    print(f"Final state - Is alerting: {bridge.is_active()}")
    print("\n✅ Test hoàn thành!")
