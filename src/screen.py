"""
Windows Arena AI — Screen Capture & Streaming
Captures the desktop screen, encodes to JPEG, and provides frames for streaming.
"""
import io
import time
import base64
import threading
from typing import Optional

try:
    from PIL import Image
    import mss
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

from .config import Settings
from .logger import audit_log


class ScreenCapture:
    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger
        self._lock = threading.Lock()
        self._last_frame: Optional[bytes] = None
        self._streaming = False
        self._stream_thread: Optional[threading.Thread] = None

    def capture_screen(self, monitor: int = 0) -> dict:
        """
        Capture a single screenshot.
        Returns dict with: success, image_base64, width, height, format
        """
        if not HAS_DEPS:
            return {"success": False, "error": "Install dependencies: pip install Pillow mss"}

        audit_log(self.settings, "screen_capture", {"monitor": monitor})

        try:
            with mss.mss() as sct:
                mon = sct.monitors[monitor] if monitor < len(sct.monitors) else sct.monitors[0]
                screenshot = sct.grab(mon)

                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                # Downscale
                scale = self.settings.screen_scale
                if scale < 1.0:
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img = img.resize(new_size, Image.LANCZOS)

                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=self.settings.screen_quality, optimize=True)
                frame_bytes = buf.getvalue()

                with self._lock:
                    self._last_frame = frame_bytes

                return {
                    "success": True,
                    "image_base64": base64.b64encode(frame_bytes).decode("ascii"),
                    "width": img.width,
                    "height": img.height,
                    "format": "jpeg",
                    "quality": self.settings.screen_quality,
                }
        except Exception as e:
            self.logger.error(f"Screen capture failed: {e}")
            return {"success": False, "error": str(e)}

    def get_last_frame(self) -> Optional[bytes]:
        with self._lock:
            return self._last_frame

    def get_screen_info(self) -> dict:
        """Return info about all monitors."""
        if not HAS_DEPS:
            return {"success": False, "error": "Install dependencies: pip install Pillow mss"}
        try:
            with mss.mss() as sct:
                monitors = []
                for i, mon in enumerate(sct.monitors):
                    monitors.append({
                        "index": i,
                        "left": mon["left"],
                        "top": mon["top"],
                        "width": mon["width"],
                        "height": mon["height"],
                    })
                return {"success": True, "monitors": monitors}
        except Exception as e:
            return {"success": False, "error": str(e)}
