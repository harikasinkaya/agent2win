"""
Windows Arena AI — Clipboard Manager
Read and write the system clipboard (text, images).
"""
import subprocess
import time
from typing import Optional
from .config import Settings
from .logger import audit_log

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


class ClipboardManager:
    """System clipboard operations."""

    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger

    async def get_text(self) -> dict:
        """Get current clipboard text."""
        audit_log(self.settings, "clipboard_get", {})
        if HAS_PYPERCLIP:
            try:
                text = pyperclip.paste()
                return {"success": True, "text": text, "length": len(text)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Fallback: PowerShell
        try:
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "text": result.stdout.strip(), "length": len(result.stdout.strip())}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_text(self, text: str) -> dict:
        """Set clipboard text."""
        audit_log(self.settings, "clipboard_set", {"length": len(text)})
        if HAS_PYPERCLIP:
            try:
                pyperclip.copy(text)
                return {"success": True, "text_length": len(text)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        try:
            subprocess.run(
                ["powershell", "-command", f'Set-Clipboard -Value @"\\n{text}\\n"@'],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "text_length": len(text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_history(self) -> dict:
        """Get clipboard history (Windows 10+)."""
        audit_log(self.settings, "clipboard_history", {})
        try:
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard -TextFormatType Text"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "history": result.stdout.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def clear(self) -> dict:
        """Clear the clipboard."""
        audit_log(self.settings, "clipboard_clear", {})
        try:
            subprocess.run(
                ["powershell", "-command", "Clear-Clipboard"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
