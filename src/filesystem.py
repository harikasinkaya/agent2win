"""
agent2win — Filesystem Browser & Manager
Browse, read, create, and manage files/directories on the Windows machine.
"""
import os
import shutil
import stat
import time
from pathlib import Path
from typing import Optional, List
from .config import Settings
from .logger import audit_log


class FilesystemManager:
    def __init__(self, settings: Settings, logger, approval_callback=None):
        self.settings = settings
        self.logger = logger
        self.approval_callback = approval_callback

    async def _approve(self, action: str, details: dict) -> bool:
        if self.settings.unrestricted_mode:
            return True
        if not self.settings.require_approval:
            return True
        # Read-only actions are auto-approved
        if action in ("list_dir", "read_file", "get_info", "search_files"):
            return True
        if self.approval_callback:
            return await self.approval_callback(action, details)
        return False

    async def list_dir(self, path: str = "C:\\", show_hidden: bool = False) -> dict:
        """List contents of a directory."""
        audit_log(self.settings, "list_dir", {"path": path})
        try:
            p = Path(path)
            if not p.exists():
                return {"success": False, "error": f"Path does not exist: {path}"}
            if not p.is_dir():
                return {"success": False, "error": f"Not a directory: {path}"}

            entries = []
            for item in sorted(p.iterdir()):
                if not show_hidden and item.name.startswith("."):
                    continue
                try:
                    st = item.stat()
                    entries.append({
                        "name": item.name,
                        "path": str(item),
                        "is_dir": item.is_dir(),
                        "size_bytes": st.st_size if item.is_file() else None,
                        "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                        "readonly": not os.access(item, os.W_OK),
                    })
                except (PermissionError, OSError):
                    entries.append({"name": item.name, "path": str(item), "error": "access denied"})

            return {"success": True, "path": str(p), "count": len(entries), "entries": entries}
        except PermissionError:
            return {"success": False, "error": f"Permission denied: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def read_file(self, path: str, max_bytes: int = 1024 * 100, encoding: str = "utf-8") -> dict:
        """Read a text file (default max 100KB)."""
        audit_log(self.settings, "read_file", {"path": path})
        try:
            p = Path(path)
            if not p.exists():
                return {"success": False, "error": f"File not found: {path}"}
            if not p.is_file():
                return {"success": False, "error": f"Not a file: {path}"}
            size = p.stat().st_size
            if size > max_bytes:
                return {"success": False, "error": f"File too large ({size} bytes). Max: {max_bytes}", "size": size}
            content = p.read_text(encoding=encoding, errors="replace")
            return {"success": True, "path": str(p), "content": content, "size": size, "encoding": encoding}
        except PermissionError:
            return {"success": False, "error": f"Permission denied: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def write_file(self, path: str, content: str, encoding: str = "utf-8") -> dict:
        """Write/create a text file."""
        if not await self._approve("write_file", {"path": path}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "write_file", {"path": path, "content_length": len(content)})
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding=encoding)
            return {"success": True, "path": str(p), "bytes_written": len(content.encode(encoding))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_file(self, path: str) -> dict:
        """Delete a file."""
        if not await self._approve("delete_file", {"path": path}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "delete_file", {"path": path})
        try:
            p = Path(path)
            if not p.exists():
                return {"success": False, "error": f"Not found: {path}"}
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return {"success": True, "deleted": str(p)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_dir(self, path: str) -> dict:
        """Create a directory (and parents)."""
        if not await self._approve("create_dir", {"path": path}):
            return {"success": False, "error": "Denied by user"}
        audit_log(self.settings, "create_dir", {"path": path})
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return {"success": True, "created": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_drives(self) -> dict:
        """List available drives on Windows."""
        audit_log(self.settings, "get_drives", {})
        try:
            import string
            drives = []
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        total, used, free = shutil.disk_usage(drive)
                        drives.append({
                            "letter": letter,
                            "path": drive,
                            "total_gb": round(total / (1024**3), 2),
                            "used_gb": round(used / (1024**3), 2),
                            "free_gb": round(free / (1024**3), 2),
                        })
                    except Exception:
                        drives.append({"letter": letter, "path": drive})
            return {"success": True, "drives": drives}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def search_files(self, directory: str, pattern: str, max_results: int = 50) -> dict:
        """Search for files matching a glob pattern."""
        audit_log(self.settings, "search_files", {"directory": directory, "pattern": pattern})
        try:
            p = Path(directory)
            if not p.exists():
                return {"success": False, "error": f"Directory not found: {directory}"}
            results = []
            for match in p.rglob(pattern):
                if len(results) >= max_results:
                    break
                try:
                    results.append({
                        "path": str(match),
                        "name": match.name,
                        "is_dir": match.is_dir(),
                        "size": match.stat().st_size if match.is_file() else None,
                    })
                except (PermissionError, OSError):
                    pass
            return {"success": True, "pattern": pattern, "count": len(results), "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_file_info(self, path: str) -> dict:
        """Get detailed info about a file or directory."""
        audit_log(self.settings, "get_info", {"path": path})
        try:
            p = Path(path)
            if not p.exists():
                return {"success": False, "error": f"Not found: {path}"}
            st = p.stat()
            return {
                "success": True,
                "path": str(p),
                "name": p.name,
                "is_dir": p.is_dir(),
                "is_file": p.is_file(),
                "size": st.st_size,
                "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_ctime)),
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                "accessed": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_atime)),
                "readonly": not os.access(p, os.W_OK),
                "hidden": bool(p.name.startswith(".")),
                "extension": p.suffix,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
