"""
Windows Arena AI — Windows Services Manager
List, start, stop, and manage Windows services.
"""
import subprocess
from typing import Optional
from .config import Settings
from .logger import audit_log

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class ServicesManager:
    """Windows services management."""

    def __init__(self, settings: Settings, logger, approval_callback=None):
        self.settings = settings
        self.logger = logger
        self.approval_callback = approval_callback

    async def _approve(self, action: str, details: dict) -> bool:
        if self.settings.unrestricted_mode:
            return True
        if action == "list_services":
            return True
        if self.approval_callback:
            return await self.approval_callback(action, details)
        return False

    async def list_services(self, filter_name: Optional[str] = None) -> dict:
        """List Windows services."""
        audit_log(self.settings, "list_services", {"filter": filter_name})
        try:
            result = subprocess.run(
                ["sc", "query", "type=", "service", "state=", "all"],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            services = []
            current = {}
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line.startswith("SERVICE_NAME"):
                    if current:
                        services.append(current)
                    name = line.split(":", 1)[1].strip() if ":" in line else ""
                    current = {"name": name, "display_name": "", "state": "", "type": ""}
                elif line.startswith("DISPLAY_NAME"):
                    current["display_name"] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif "STATE" in line and ":" in line:
                    parts = line.split()
                    for p in parts:
                        if p.startswith("RUNNING") or p.startswith("STOPPED") or p.startswith("PAUSED"):
                            current["state"] = p
                elif "TYPE" in line and ":" in line:
                    current["type"] = line.split(":", 1)[1].strip()
            if current:
                services.append(current)

            if filter_name:
                services = [s for s in services if filter_name.lower() in s["name"].lower() or filter_name.lower() in s.get("display_name", "").lower()]

            return {"success": True, "services": services[:100], "total": len(services)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def start_service(self, name: str) -> dict:
        """Start a Windows service."""
        if not await self._approve("start_service", {"name": name}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "start_service", {"name": name})
        try:
            result = subprocess.run(
                ["sc", "start", name],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "name": name, "output": result.stdout.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def stop_service(self, name: str) -> dict:
        """Stop a Windows service."""
        if not await self._approve("stop_service", {"name": name}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "stop_service", {"name": name})
        try:
            result = subprocess.run(
                ["sc", "stop", name],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "name": name, "output": result.stdout.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def restart_service(self, name: str) -> dict:
        """Restart a Windows service."""
        if not await self._approve("restart_service", {"name": name}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "restart_service", {"name": name})
        stop = await self.stop_service(name)
        if stop.get("success"):
            import asyncio
            await asyncio.sleep(2)
            return await self.start_service(name)
        return stop

    async def get_service_status(self, name: str) -> dict:
        """Get detailed status of a service."""
        audit_log(self.settings, "get_service_status", {"name": name})
        try:
            result = subprocess.run(
                ["sc", "query", name],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "name": name, "output": result.stdout.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}
