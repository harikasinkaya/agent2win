"""
agent2win — Command Execution Engine
Runs shell commands with safety checks, timeouts, and approval flow.
"""
import subprocess
import shlex
import time
import threading
import asyncio
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

    async def execute(self, cmd: str, cwd: Optional[str] = None, timeout: Optional[int] = None, background: bool = False) -> dict:
        """
        Execute a Windows command. Returns dict with:
          success, stdout, stderr, returncode, duration_sec, approved, (pid if background)
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

        audit_log(self.settings, "command_executed", {"cmd": cmd, "cwd": cwd, "background": background}, approved=True)
        self.logger.info(f"Executing: {cmd} {'[BACKGROUND]' if background else ''}")

        cmd_strip = cmd.strip().lower()
        # Auto-detect long running servers if background not explicitly set
        if background or cmd_strip.startswith("start ") or cmd_strip.startswith("npm start") or cmd_strip.startswith("npm run dev") or cmd_strip.startswith("node server") or cmd_strip.startswith("node index") or cmd_strip.startswith("node app") or cmd_strip.startswith("python -m http.server"):
            try:
                proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=cwd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                )
                return {
                    "success": True,
                    "background": True,
                    "pid": proc.pid,
                    "stdout": f"Started in background (PID: {proc.pid})",
                    "stderr": "",
                    "returncode": 0,
                    "approved": approved,
                }
            except Exception as e:
                return {"success": False, "error": str(e), "stdout": "", "stderr": "", "returncode": -1}

        effective_timeout = timeout or self.settings.max_command_timeout_sec
        t0 = time.time()

        try:
            loop = asyncio.get_running_loop()
            def _run():
                return subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=effective_timeout,
                    encoding="utf-8",
                    errors="replace",
                )
            proc = await loop.run_in_executor(None, _run)
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
            return {"success": False, "error": f"Command timed out after {effective_timeout}s (Tip: use \"background\": true for servers/long scripts)", "stdout": "", "stderr": "", "returncode": -1}
        except Exception as e:
            return {"success": False, "error": str(e), "stdout": "", "stderr": "", "returncode": -1}
