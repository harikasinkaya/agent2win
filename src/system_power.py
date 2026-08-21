"""
Windows Arena AI — System Power & Lock Controls
Shutdown, restart, sleep, lock, hibernate.
"""
import subprocess
import ctypes
import time
from typing import Optional
from .config import Settings
from .logger import audit_log


class SystemPower:
    """System power management."""

    def __init__(self, settings: Settings, logger, approval_callback=None):
        self.settings = settings
        self.logger = logger
        self.approval_callback = approval_callback

    async def _approve(self, action: str, details: dict) -> bool:
        if self.settings.unrestricted_mode:
            return True
        if self.approval_callback:
            return await self.approval_callback(action, details)
        return False

    async def lock(self) -> dict:
        """Lock the workstation."""
        audit_log(self.settings, "system_lock", {})
        try:
            ctypes.windll.user32.LockWorkStation()
            return {"success": True, "action": "locked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def shutdown(self, delay_sec: int = 0) -> dict:
        """Shutdown the computer."""
        if not await self._approve("system_shutdown", {"delay": delay_sec}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "system_shutdown", {"delay": delay_sec})
        try:
            cmd = f"shutdown /s /t {delay_sec}"
            subprocess.Popen(cmd, shell=True)
            return {"success": True, "action": "shutdown", "delay_sec": delay_sec}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def restart(self, delay_sec: int = 0) -> dict:
        """Restart the computer."""
        if not await self._approve("system_restart", {"delay": delay_sec}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "system_restart", {"delay": delay_sec})
        try:
            cmd = f"shutdown /r /t {delay_sec}"
            subprocess.Popen(cmd, shell=True)
            return {"success": True, "action": "restart", "delay_sec": delay_sec}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def cancel_shutdown(self) -> dict:
        """Cancel a pending shutdown/restart."""
        audit_log(self.settings, "cancel_shutdown", {})
        try:
            subprocess.run(["shutdown", "/a"], capture_output=True, timeout=5)
            return {"success": True, "action": "cancelled"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def sleep(self) -> dict:
        """Put the computer to sleep."""
        if not await self._approve("system_sleep", {}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "system_sleep", {})
        try:
            subprocess.run(
                ["powershell", "-command", "Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState($false, $true, $false)"],
                capture_output=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "action": "sleep"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def hibernate(self) -> dict:
        """Hibernate the computer."""
        if not await self._approve("system_hibernate", {}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "system_hibernate", {})
        try:
            subprocess.run(
                ["powershell", "-command", "Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState($true, $true, $false)"],
                capture_output=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "action": "hibernate"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def logoff(self) -> dict:
        """Log off the current user."""
        if not await self._approve("system_logoff", {}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "system_logoff", {})
        try:
            subprocess.run(["shutdown", "/l"], capture_output=True, timeout=5)
            return {"success": True, "action": "logoff"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_uptime(self) -> dict:
        """Get system uptime."""
        try:
            import psutil
            boot = psutil.boot_time()
            uptime_sec = time.time() - boot
            days = int(uptime_sec // 86400)
            hours = int((uptime_sec % 86400) // 3600)
            minutes = int((uptime_sec % 3600) // 60)
            return {
                "success": True,
                "uptime_sec": round(uptime_sec),
                "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot)),
                "formatted": f"{days}d {hours}h {minutes}m",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def empty_trash(self) -> dict:
        """Empty the Recycle Bin."""
        if not await self._approve("empty_trash", {}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "empty_trash", {})
        try:
            subprocess.run(
                ["powershell", "-command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "action": "trash_emptied"}
        except Exception as e:
            return {"success": False, "error": str(e)}
