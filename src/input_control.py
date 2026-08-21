"""
Windows Arena AI — Input Control (Mouse & Keyboard)
Simulates mouse clicks, movement, scrolling, and keyboard input.
"""
import time
from typing import Optional, List

try:
    import pyautogui
    pyautogui.FAILSAFE = True   # Move mouse to corner to abort
    pyautogui.PAUSE = 0.05
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

from .config import Settings
from .logger import audit_log


class InputController:
    def __init__(self, settings: Settings, logger, approval_callback=None):
        self.settings = settings
        self.logger = logger
        self.approval_callback = approval_callback

    def _check_deps(self) -> Optional[dict]:
        if not HAS_DEPS:
            return {"success": False, "error": "Install dependencies: pip install pyautogui"}
        return None

    async def _approve(self, action: str, details: dict) -> bool:
        if self.settings.unrestricted_mode:
            return True
        if not self.settings.require_approval:
            return True
        if self.approval_callback:
            return await self.approval_callback(action, details)
        return False

    async def mouse_move(self, x: int, y: int) -> dict:
        dep = self._check_deps()
        if dep: return dep
        if not await self._approve("mouse_move", {"x": x, "y": y}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "mouse_move", {"x": x, "y": y})
        pyautogui.moveTo(x, y, duration=0.15)
        return {"success": True, "action": "mouse_move", "x": x, "y": y}

    async def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> dict:
        dep = self._check_deps()
        if dep: return dep
        if not await self._approve("mouse_click", {"x": x, "y": y, "button": button, "clicks": clicks}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "mouse_click", {"x": x, "y": y, "button": button, "clicks": clicks})
        pyautogui.click(x, y, clicks=clicks, button=button)
        return {"success": True, "action": "mouse_click", "x": x, "y": y, "button": button}

    async def mouse_double_click(self, x: int, y: int) -> dict:
        return await self.mouse_click(x, y, button="left", clicks=2)

    async def mouse_right_click(self, x: int, y: int) -> dict:
        return await self.mouse_click(x, y, button="right", clicks=1)

    async def mouse_drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> dict:
        dep = self._check_deps()
        if dep: return dep
        if not await self._approve("mouse_drag", {"x1": x1, "y1": y1, "x2": x2, "y2": y2}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "mouse_drag", {"x1": x1, "y1": y1, "x2": x2, "y2": y2})
        pyautogui.moveTo(x1, y1)
        pyautogui.drag(x2 - x1, y2 - y1, duration=duration)
        return {"success": True, "action": "mouse_drag"}

    async def mouse_scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> dict:
        dep = self._check_deps()
        if dep: return dep
        if not await self._approve("mouse_scroll", {"clicks": clicks, "x": x, "y": y}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "mouse_scroll", {"clicks": clicks})
        if x is not None and y is not None:
            pyautogui.moveTo(x, y)
        pyautogui.scroll(clicks)
        return {"success": True, "action": "mouse_scroll", "clicks": clicks}

    async def type_text(self, text: str, interval: float = 0.02) -> dict:
        dep = self._check_deps()
        if dep: return dep
        if not await self._approve("type_text", {"text_length": len(text)}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "type_text", {"text_length": len(text)})
        pyautogui.typewrite(text, interval=interval) if text.isascii() else pyautogui.write(text)
        return {"success": True, "action": "type_text", "length": len(text)}

    async def type_unicode(self, text: str) -> dict:
        """Type text with full Unicode support (including Cyrillic, CJK, etc.)"""
        dep = self._check_deps()
        if dep: return dep
        if not await self._approve("type_unicode", {"text_length": len(text)}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "type_unicode", {"text_length": len(text)})
        try:
            import pyperclip
            old = pyperclip.paste()
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)
            pyperclip.copy(old)
        except ImportError:
            # Fallback: use pyautogui.write (ASCII only)
            pyautogui.write(text)
        return {"success": True, "action": "type_unicode", "length": len(text)}

    async def press_key(self, key: str) -> dict:
        dep = self._check_deps()
        if dep: return dep
        if not await self._approve("press_key", {"key": key}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "press_key", {"key": key})
        pyautogui.press(key)
        return {"success": True, "action": "press_key", "key": key}

    async def hotkey(self, *keys: str) -> dict:
        dep = self._check_deps()
        if dep: return dep
        if not await self._approve("hotkey", {"keys": list(keys)}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "hotkey", {"keys": list(keys)})
        pyautogui.hotkey(*keys)
        return {"success": True, "action": "hotkey", "keys": list(keys)}

    async def key_down(self, key: str) -> dict:
        dep = self._check_deps()
        if dep: return dep
        audit_log(self.settings, "key_down", {"key": key})
        pyautogui.keyDown(key)
        return {"success": True, "action": "key_down", "key": key}

    async def key_up(self, key: str) -> dict:
        dep = self._check_deps()
        if dep: return dep
        audit_log(self.settings, "key_up", {"key": key})
        pyautogui.keyUp(key)
        return {"success": True, "action": "key_up", "key": key}

    def get_mouse_position(self) -> dict:
        if not HAS_DEPS:
            return {"success": False, "error": "Install dependencies: pip install pyautogui"}
        pos = pyautogui.position()
        return {"success": True, "x": pos.x, "y": pos.y}

    def get_screen_size(self) -> dict:
        if not HAS_DEPS:
            return {"success": False, "error": "Install dependencies: pip install pyautogui"}
        size = pyautogui.size()
        return {"success": True, "width": size.width, "height": size.height}
