"""
Windows Arena AI — Command Execution Engine
Runs shell commands with safety checks, timeouts, and approval flow.
"""
import subprocess
import shlex
import time
import threading
from typing import Optional
from .config import Settings
from .logger import audit_log

class CommandEngine:
    def __init__(self, settings: Settings, logger, approval_callback=None):
        self.settings = settings
        self.logger = logger
        self.approval_callback = approval_callback  # async fn(action, details) -> bool

    def _is_blocked(self, cmd: str) -> bool:
        cmd_lower = cmd.lower().strip()
        for blocked in self.settings.blocked_commands:
            if blocked.lower() in cmd_lower:
                return True
        return False

    def _needs_approval(self, cmd: str) -> bool:
        if self.settings.unrestricted_mode:
            return False
        if not self.settings.require_approval:
            return False
        cmd_lower = cmd.lower().strip()
        # Known safe read-only commands pass without approval
        safe_prefixes = ("dir", "cd", "echo", "whoami", "hostname", "ipconfig",
                         "systeminfo", "tasklist", "where", "type", "tree",
                         "netstat", "ping", "tracert", "ver", "date", "time")
        for safe in safe_prefixes:
            if cmd_lower.startswith(safe):
                return False
        return True

    async def execute(self, cmd: str, cwd: Optional[str] = None, timeout: Optional[int] = None) -> dict:
        """
        Execute a Windows command. Returns dict with:
          success, stdout, stderr, returncode, duration_sec, approved
        """
        if self._is_blocked(cmd):
            audit_log(self.settings, "command_blocked", {"cmd": cmd}, approved=False)
            return {"success": False, "error": f"Command blocked by security policy: {cmd}", "stdout": "", "stderr": "", "returncode": -1}

        approved = True
        if self._needs_approval(cmd):
            if self.approval_callback:
                approved = await self.approval_callback("command", {"cmd": cmd, "cwd": cwd})
            else:
                approved = False
            if not approved:
                audit_log(self.settings, "command_denied", {"cmd": cmd}, approved=False)
                return {"success": False, "error": "Command denied by user", "stdout": "", "stderr": "", "returncode": -1}

        audit_log(self.settings, "command_executed", {"cmd": cmd, "cwd": cwd}, approved=True)
        self.logger.info(f"Executing: {cmd}")

        effective_timeout = timeout or self.settings.max_command_timeout_sec
        t0 = time.time()

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=effective_timeout,
                encoding="utf-8",
                errors="replace",
            )
            duration = round(time.time() - t0, 3)
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
                "duration_sec": duration,
                "approved": approved,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {effective_timeout}s", "stdout": "", "stderr": "", "returncode": -1}
        except Exception as e:
            return {"success": False, "error": str(e), "stdout": "", "stderr": "", "returncode": -1}
