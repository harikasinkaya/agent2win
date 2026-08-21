"""
Windows Arena AI — Process Manager
List, launch, and manage Windows processes.
"""
import subprocess
import os
import signal
from typing import Optional
from .config import Settings
from .logger import audit_log

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class ProcessManager:
    def __init__(self, settings: Settings, logger, approval_callback=None):
        self.settings = settings
        self.logger = logger
        self.approval_callback = approval_callback

    async def _approve(self, action: str, details: dict) -> bool:
        if self.settings.unrestricted_mode:
            return True
        if not self.settings.require_approval:
            return True
        if action == "list_processes":
            return True
        if self.approval_callback:
            return await self.approval_callback(action, details)
        return False

    async def list_processes(self, filter_name: Optional[str] = None) -> dict:
        """List running processes."""
        audit_log(self.settings, "list_processes", {"filter": filter_name})
        if not HAS_PSUTIL:
            # Fallback to tasklist
            try:
                result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10)
                lines = result.stdout.strip().split("\n")
                processes = []
                for line in lines[:100]:
                    parts = line.strip('"').split('","')
                    if len(parts) >= 5:
                        processes.append({
                            "name": parts[0],
                            "pid": int(parts[1]),
                            "session": parts[2],
                            "mem_usage": parts[4],
                        })
                return {"success": True, "processes": processes, "count": len(processes)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status", "username"]):
            try:
                info = proc.info
                if filter_name and filter_name.lower() not in info["name"].lower():
                    continue
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"],
                    "memory_mb": round(info["memory_info"].rss / (1024 * 1024), 1) if info["memory_info"] else None,
                    "status": info["status"],
                    "username": info["username"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return {"success": True, "processes": processes[:200], "count": len(processes)}

    async def launch_program(self, path: str, args: str = "", cwd: Optional[str] = None) -> dict:
        """Launch a program."""
        if not await self._approve("launch_program", {"path": path, "args": args}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "launch_program", {"path": path, "args": args})
        try:
            if args:
                cmd = f'"{path}" {args}'
            else:
                cmd = f'"{path}"'
            proc = subprocess.Popen(
                cmd, shell=True, cwd=cwd,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            return {"success": True, "pid": proc.pid, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def kill_process(self, pid: int) -> dict:
        """Kill a process by PID."""
        if not await self._approve("kill_process", {"pid": pid}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "kill_process", {"pid": pid})
        try:
            if HAS_PSUTIL:
                proc = psutil.Process(pid)
                name = proc.name()
                proc.terminate()
                proc.wait(timeout=5)
                return {"success": True, "killed": name, "pid": pid}
            else:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=10)
                return {"success": True, "killed_pid": pid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_system_info(self) -> dict:
        """Get system information."""
        audit_log(self.settings, "system_info", {})
        info = {"success": True}
        try:
            import platform
            info["os"] = platform.system()
            info["os_version"] = platform.version()
            info["os_release"] = platform.release()
            info["machine"] = platform.machine()
            info["processor"] = platform.processor()
            info["hostname"] = platform.node()
            info["python_version"] = platform.python_version()
        except Exception:
            pass

        if HAS_PSUTIL:
            try:
                info["cpu_count"] = psutil.cpu_count()
                info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
                mem = psutil.virtual_memory()
                info["ram_total_gb"] = round(mem.total / (1024**3), 2)
                info["ram_used_gb"] = round(mem.used / (1024**3), 2)
                info["ram_percent"] = mem.percent
                disk = psutil.disk_usage("C:\\")
                info["disk_total_gb"] = round(disk.total / (1024**3), 2)
                info["disk_used_gb"] = round(disk.used / (1024**3), 2)
                info["disk_percent"] = round(disk.percent, 1)
            except Exception:
                pass

        return info
