"""
agent2win — System Tray Application
Provides a system tray icon with quick access to settings, approvals, and status.
"""
import threading
import webbrowser
import time
from typing import Optional

from .config import Settings

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def create_icon_image(color: str = "#00d4ff", size: int = 64) -> "Image.Image":
    """Create a simple icon for the system tray."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw a rounded square with "A2W" text
    draw.rounded_rectangle([4, 4, size - 4, size - 4], radius=12, fill=color)
    draw.text((size // 2 - 12, size // 2 - 12), "A2W", fill="white")
    return img


class TrayApp:
    """System tray application for Windows Arena AI."""

    def __init__(self, settings: Settings, notifications, server_port: int):
        self.settings = settings
        self.notifications = notifications  # Can be None initially
        self.server_port = server_port
        self._icon: Optional["pystray.Icon"] = None
        self._thread: Optional[threading.Thread] = None

    def set_notifications(self, notifications):
        """Set the notification manager (called after server is created)."""
        self.notifications = notifications

    def _open_web_ui(self, icon=None, item=None):
        webbrowser.open(f"http://localhost:{self.server_port}")

    def _toggle_unrestricted(self, icon=None, item=None):
        self.settings.unrestricted_mode = not self.settings.unrestricted_mode
        self.settings.save()
        # Update icon color
        if self._icon:
            color = "#ff4444" if self.settings.unrestricted_mode else "#00d4ff"
            self._icon.icon = create_icon_image(color)

    def _approve_all(self, icon=None, item=None):
        if self.notifications:
            self.notifications.approve_all()

    def _deny_all(self, icon=None, item=None):
        if self.notifications:
            self.notifications.deny_all()

    def _quit(self, icon=None, item=None):
        if self._icon:
            self._icon.stop()

    def _create_menu(self):
        if not HAS_TRAY:
            return None

        pending_count = len(self.notifications.get_pending()) if self.notifications else 0
        unrestricted_label = "🔓 Unrestricted: ON" if self.settings.unrestricted_mode else "🔒 Unrestricted: OFF"

        menu = pystray.Menu(
            pystray.MenuItem("🌐 Open Web UI", self._open_web_ui, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                unrestricted_label,
                self._toggle_unrestricted,
                checked=lambda item: self.settings.unrestricted_mode,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"⏳ Pending Approvals ({pending_count})", None, enabled=False),
            pystray.MenuItem("✅ Approve All", self._approve_all),
            pystray.MenuItem("❌ Deny All", self._deny_all),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🚪 Quit", self._quit),
        )
        return menu

    def start(self):
        """Start the system tray icon in a background thread."""
        if not HAS_TRAY:
            print("⚠️ System tray not available (install: pip install pystray Pillow)")
            print(f"   Web UI available at: http://localhost:{self.server_port}")
            return

        color = "#ff4444" if self.settings.unrestricted_mode else "#00d4ff"
        self._icon = pystray.Icon(
            "WindowsArenaAI",
            create_icon_image(color),
            "Windows Arena AI",
            menu=self._create_menu(),
        )

        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._icon:
            self._icon.stop()
