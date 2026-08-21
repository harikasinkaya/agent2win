"""
agent2win — Registry Manager
Read and write Windows registry keys.
"""
import subprocess
import winreg
from typing import Optional, Any
from .config import Settings
from .logger import audit_log

HIVE_MAP = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKU": winreg.HKEY_USERS,
    "HKCC": winreg.HKEY_CURRENT_CONFIG,
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
    "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
    "HKEY_USERS": winreg.HKEY_USERS,
    "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG,
}

TYPE_MAP = {
    winreg.REG_SZ: "string",
    winreg.REG_EXPAND_SZ: "expand_string",
    winreg.REG_BINARY: "binary",
    winreg.REG_DWORD: "dword",
    winreg.REG_QWORD: "qword",
    winreg.REG_MULTI_SZ: "multi_string",
}


class RegistryManager:
    """Windows Registry operations."""

    def __init__(self, settings: Settings, logger, approval_callback=None):
        self.settings = settings
        self.logger = logger
        self.approval_callback = approval_callback

    async def _approve(self, action: str, details: dict) -> bool:
        if self.settings.unrestricted_mode:
            return True
        if action == "reg_read":
            return True
        if self.approval_callback:
            return await self.approval_callback(action, details)
        return False

    async def read_key(self, hive: str, path: str, name: str = "") -> dict:
        """Read a registry value."""
        audit_log(self.settings, "reg_read", {"hive": hive, "path": path, "name": name})
        try:
            h = HIVE_MAP.get(hive.upper())
            if h is None:
                return {"success": False, "error": f"Unknown hive: {hive}"}
            key = winreg.OpenKey(h, path, 0, winreg.KEY_READ)
            value, reg_type = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return {
                "success": True,
                "value": value,
                "type": TYPE_MAP.get(reg_type, str(reg_type)),
                "hive": hive,
                "path": path,
                "name": name or "(Default)",
            }
        except FileNotFoundError:
            return {"success": False, "error": f"Key not found: {hive}\\{path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_subkeys(self, hive: str, path: str) -> dict:
        """List subkeys of a registry key."""
        audit_log(self.settings, "reg_list", {"hive": hive, "path": path})
        try:
            h = HIVE_MAP.get(hive.upper())
            if h is None:
                return {"success": False, "error": f"Unknown hive: {hive}"}
            key = winreg.OpenKey(h, path, 0, winreg.KEY_READ)
            subkeys = []
            values = []

            # Enumerate subkeys
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(key, i)
                    subkeys.append(subkey)
                    i += 1
                except OSError:
                    break

            # Enumerate values
            i = 0
            while True:
                try:
                    name, value, reg_type = winreg.EnumValue(key, i)
                    values.append({
                        "name": name or "(Default)",
                        "value": value,
                        "type": TYPE_MAP.get(reg_type, str(reg_type)),
                    })
                    i += 1
                except OSError:
                    break

            winreg.CloseKey(key)
            return {"success": True, "subkeys": subkeys, "values": values, "subkey_count": len(subkeys), "value_count": len(values)}
        except FileNotFoundError:
            return {"success": False, "error": f"Key not found: {hive}\\{path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def write_key(self, hive: str, path: str, name: str, value: Any, reg_type: str = "string") -> dict:
        """Write a registry value."""
        if not await self._approve("reg_write", {"hive": hive, "path": path, "name": name}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "reg_write", {"hive": hive, "path": path, "name": name})
        try:
            h = HIVE_MAP.get(hive.upper())
            if h is None:
                return {"success": False, "error": f"Unknown hive: {hive}"}

            type_map = {
                "string": winreg.REG_SZ,
                "expand_string": winreg.REG_EXPAND_SZ,
                "dword": winreg.REG_DWORD,
                "qword": winreg.REG_QWORD,
                "multi_string": winreg.REG_MULTI_SZ,
                "binary": winreg.REG_BINARY,
            }
            rt = type_map.get(reg_type.lower(), winreg.REG_SZ)

            key = winreg.CreateKeyEx(h, path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, name, 0, rt, value)
            winreg.CloseKey(key)
            return {"success": True, "written": f"{hive}\\{path}\\{name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_key(self, hive: str, path: str, name: str = "") -> dict:
        """Delete a registry key or value."""
        if not await self._approve("reg_delete", {"hive": hive, "path": path, "name": name}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "reg_delete", {"hive": hive, "path": path, "name": name})
        try:
            h = HIVE_MAP.get(hive.upper())
            if h is None:
                return {"success": False, "error": f"Unknown hive: {hive}"}
            if name:
                key = winreg.OpenKey(h, path, 0, winreg.KEY_WRITE)
                winreg.DeleteValue(key, name)
                winreg.CloseKey(key)
            else:
                winreg.DeleteKey(h, path)
            return {"success": True, "deleted": f"{hive}\\{path}" + (f"\\{name}" if name else "")}
        except Exception as e:
            return {"success": False, "error": str(e)}
