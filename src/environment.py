"""
agent2win — Environment & System Info
Environment variables, installed programs, startup items, scheduled tasks.
"""
import subprocess
import os
import winreg
from typing import Optional
from .config import Settings
from .logger import audit_log

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class EnvironmentManager:
    """System environment and configuration."""

    def __init__(self, settings: Settings, logger, approval_callback=None):
        self.settings = settings
        self.logger = logger
        self.approval_callback = approval_callback

    async def _approve(self, action: str, details: dict) -> bool:
        if self.settings.unrestricted_mode:
            return True
        if action in ("get_env", "list_programs", "list_startup", "list_tasks", "get_path"):
            return True
        if self.approval_callback:
            return await self.approval_callback(action, details)
        return False

    async def get_env_vars(self, scope: str = "user") -> dict:
        """Get environment variables."""
        audit_log(self.settings, "get_env", {"scope": scope})
        try:
            if scope == "process":
                env = dict(os.environ)
            elif scope == "system":
                result = subprocess.run(
                    ["reg", "query", r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                env = {}
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if "    " in line and "REG_" in line:
                        parts = line.split("    ", 2)
                        if len(parts) >= 3:
                            env[parts[0].strip()] = parts[2].strip()
            else:  # user
                result = subprocess.run(
                    ["reg", "query", r"HKCU\Environment"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                env = {}
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if "    " in line and "REG_" in line:
                        parts = line.split("    ", 2)
                        if len(parts) >= 3:
                            env[parts[0].strip()] = parts[2].strip()

            return {"success": True, "scope": scope, "variables": env, "count": len(env)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_env_var(self, name: str, value: str, scope: str = "user") -> dict:
        """Set an environment variable."""
        if not await self._approve("set_env", {"name": name, "scope": scope}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "set_env", {"name": name, "scope": scope})
        try:
            if scope == "process":
                os.environ[name] = value
                return {"success": True, "scope": "process"}
            target = "HKCU\\Environment" if scope == "user" else r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
            subprocess.run(
                ["reg", "add", target, "/v", name, "/t", "REG_SZ", "/d", value, "/f"],
                capture_output=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "name": name, "scope": scope}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_installed_programs(self) -> dict:
        """List installed programs."""
        audit_log(self.settings, "list_programs", {})
        programs = []
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, path in reg_paths:
            try:
                key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            version = ""
                            publisher = ""
                            install_date = ""
                            try:
                                version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                            except Exception:
                                pass
                            try:
                                publisher = winreg.QueryValueEx(subkey, "Publisher")[0]
                            except Exception:
                                pass
                            try:
                                install_date = winreg.QueryValueEx(subkey, "InstallDate")[0]
                            except Exception:
                                pass
                            programs.append({
                                "name": name,
                                "version": version,
                                "publisher": publisher,
                                "install_date": install_date,
                            })
                        except Exception:
                            pass
                        winreg.CloseKey(subkey)
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception:
                pass

        programs.sort(key=lambda x: x["name"].lower())
        return {"success": True, "programs": programs, "count": len(programs)}

    async def list_startup_items(self) -> dict:
        """List startup programs."""
        audit_log(self.settings, "list_startup", {})
        items = []
        try:
            result = subprocess.run(
                ["wmic", "startup", "get", "name,command,location", "/format:csv"],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in result.stdout.split("\n")[1:]:
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    items.append({"name": parts[1] if len(parts) > 1 else "", "command": parts[2] if len(parts) > 2 else "", "location": parts[0]})
        except Exception:
            pass

        # Also check registry startup
        startup_keys = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        ]
        for hive, path in startup_keys:
            try:
                key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        items.append({"name": name, "command": value, "location": "HKCU" if hive == winreg.HKEY_CURRENT_USER else "HKLM"})
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception:
                pass

        return {"success": True, "startup_items": items, "count": len(items)}

    async def list_scheduled_tasks(self) -> dict:
        """List scheduled tasks."""
        audit_log(self.settings, "list_tasks", {})
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            tasks = []
            for line in result.stdout.split("\n")[:100]:
                parts = line.strip().strip('"').split('","')
                if len(parts) >= 3:
                    tasks.append({
                        "name": parts[0],
                        "next_run": parts[1] if len(parts) > 1 else "",
                        "status": parts[2] if len(parts) > 2 else "",
                    })
            return {"success": True, "tasks": tasks, "count": len(tasks)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_path(self) -> dict:
        """Get PATH environment variable as list."""
        audit_log(self.settings, "get_path", {})
        path = os.environ.get("PATH", "")
        entries = [p.strip() for p in path.split(";") if p.strip()]
        return {"success": True, "path": entries, "count": len(entries)}

    async def get_temp_dir(self) -> dict:
        """Get temp directory path and contents."""
        temp = os.environ.get("TEMP", os.environ.get("TMP", ""))
        try:
            files = os.listdir(temp)[:50]
            return {"success": True, "temp_dir": temp, "files": files, "count": len(files)}
        except Exception as e:
            return {"success": False, "error": str(e), "temp_dir": temp}
