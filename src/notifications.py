"""
agent2win — Notification & Approval System
Shows Windows toast notifications when the agent requests access.
Users can approve or deny actions from the system tray or web UI.
"""
import threading
import time
import asyncio
import ctypes
from typing import Optional, Callable
from .config import Settings
from .logger import audit_log

# Windows toast notification support
try:
    from win10toast import ToastNotifier
    HAS_TOAST = True
except ImportError:
    HAS_TOAST = False

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False


class ApprovalRequest:
    """Represents a pending approval request from the agent."""
    def __init__(self, request_id: str, action: str, details: dict, timeout: int):
        self.request_id = request_id
        self.action = action
        self.details = details
        self.timeout = timeout
        self.approved: Optional[bool] = None
        self._async_event = asyncio.Event()
        self.created_at = time.time()

    def approve(self):
        self.approved = True
        self._async_event.set()

    def deny(self):
        self.approved = False
        self._async_event.set()

    async def wait(self) -> bool:
        try:
            await asyncio.wait_for(self._async_event.wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            pass
        if self.approved is None:
            self.approved = False  # Auto-deny on timeout
        return self.approved


class NotificationManager:
    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger
        self._pending: dict[str, ApprovalRequest] = {}
        self._counter = 0
        self._lock = threading.Lock()
        self._toaster = ToastNotifier() if HAS_TOAST else None
        self._approval_gui_callback: Optional[Callable] = None

    def set_gui_callback(self, callback: Callable):
        """Set a callback to show an approval GUI dialog."""
        self._approval_gui_callback = callback

    def _format_action(self, action: str, details: dict) -> str:
        """Format action details into a human-readable string."""
        if action == "command":
            return f"🖥️ Execute command:\n{details.get('cmd', '?')}"
        elif action == "mouse_click":
            return f"🖱️ Click at ({details.get('x')}, {details.get('y')})"
        elif action == "mouse_move":
            return f"🖱️ Move mouse to ({details.get('x')}, {details.get('y')})"
        elif action == "mouse_scroll":
            return f"🖱️ Scroll ({details.get('clicks', '?')} clicks)"
        elif action == "mouse_drag":
            return f"🖱️ Drag from ({details.get('x1')},{details.get('y1')}) to ({details.get('x2')},{details.get('y2')})"
        elif action == "type_text":
            return f"⌨️ Type {details.get('text_length', '?')} characters"
        elif action == "type_unicode":
            return f"⌨️ Type {details.get('text_length', '?')} Unicode chars"
        elif action == "press_key":
            return f"⌨️ Press key: {details.get('key', '?')}"
        elif action == "hotkey":
            return f"⌨️ Hotkey: {'+'.join(details.get('keys', []))}"
        elif action == "launch_program":
            return f"🚀 Launch: {details.get('path', '?')}"
        elif action == "kill_process":
            return f"❌ Kill process PID: {details.get('pid', '?')}"
        elif action == "write_file":
            return f"📝 Write file: {details.get('path', '?')}"
        elif action == "delete_file":
            return f"🗑️ Delete: {details.get('path', '?')}"
        elif action == "create_dir":
            return f"📁 Create dir: {details.get('path', '?')}"
        else:
            return f"⚡ Action: {action} — {details}"

    async def request_approval(self, action: str, details: dict) -> bool:
        """
        Request user approval for an action.
        Shows a Windows notification and waits for user response.
        Returns True if approved, False if denied.
        """
        with self._lock:
            self._counter += 1
            req_id = f"req-{self._counter}-{int(time.time())}"

        req = ApprovalRequest(req_id, action, details, self.settings.approval_timeout_sec)
        with self._lock:
            self._pending[req_id] = req

        message = self._format_action(action, details)
        self.logger.info(f"Approval requested [{req_id}]: {message}")

        # Play alert sound (in thread to not block)
        if HAS_SOUND:
            try:
                threading.Thread(target=lambda: winsound.MessageBeep(winsound.MB_ICONEXCLAMATION), daemon=True).start()
            except Exception:
                pass

        # Show interactive modal popup box on Windows desktop
        def _show_msgbox():
            try:
                # MB_YESNO | MB_ICONQUESTION | MB_TOPMOST | MB_SETFOREGROUND
                res = ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Agent requested permission:\n\n{message}\n\nDo you want to allow this action?",
                    f"agent2win Approval [{req_id}]",
                    0x00000004 | 0x00000020 | 0x00040000 | 0x00010000
                )
                if res == 6:  # IDYES
                    req.approve()
                elif res == 7:  # IDNO
                    req.deny()
            except Exception as e:
                self.logger.warning(f"Popup dialog failed: {e}")

        threading.Thread(target=_show_msgbox, daemon=True).start()

        # If GUI callback is set, use it
        if self._approval_gui_callback:
            try:
                result = self._approval_gui_callback(req_id, action, details)
                if result is not None:
                    if result:
                        req.approve()
                    else:
                        req.deny()
            except Exception as e:
                self.logger.warning(f"GUI callback failed: {e}")

        # Wait for approval (non-blocking for asyncio)
        approved = await req.wait()

        # Cleanup
        with self._lock:
            self._pending.pop(req_id, None)

        audit_log(self.settings, f"approval_{'granted' if approved else 'denied'}",
                  {"action": action, "details": details}, approved=approved)

        self.logger.info(f"Approval {'GRANTED' if approved else 'DENIED'} [{req_id}]")
        return approved

    def approve_request(self, request_id: str) -> bool:
        """Manually approve a pending request (from web UI or tray)."""
        with self._lock:
            req = self._pending.get(request_id)
        if req:
            req.approve()
            return True
        return False

    def deny_request(self, request_id: str) -> bool:
        """Manually deny a pending request."""
        with self._lock:
            req = self._pending.get(request_id)
        if req:
            req.deny()
            return True
        return False

    def get_pending(self) -> list:
        """Get list of pending approval requests."""
        with self._lock:
            return [
                {
                    "request_id": r.request_id,
                    "action": r.action,
                    "details": r.details,
                    "age_sec": round(time.time() - r.created_at, 1),
                    "timeout_sec": r.timeout,
                }
                for r in self._pending.values()
            ]

    def approve_all(self):
        """Approve all pending requests."""
        with self._lock:
            for req in self._pending.values():
                req.approve()

    def deny_all(self):
        """Deny all pending requests."""
        with self._lock:
            for req in self._pending.values():
                req.deny()
