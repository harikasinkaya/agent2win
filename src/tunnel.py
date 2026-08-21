"""
agent2win — Tunnel Manager
Creates a free public tunnel so web & cloud AI agents can reach the Windows machine.
Supports: Cloudflare Tunnel (cloudflared), ngrok, or custom URL.
"""
import subprocess
import threading
import time
import re
import shutil
import os
from typing import Optional
from .config import Settings
from .logger import audit_log


class TunnelManager:
    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger
        self._process: Optional[subprocess.Popen] = None
        self._tunnel_url: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def tunnel_url(self) -> Optional[str]:
        return self._tunnel_url

    def _find_cloudflared(self) -> Optional[str]:
        """Find cloudflared binary."""
        # Check PATH (exe and cmd)
        for name in ["cloudflared.exe", "cloudflared.cmd", "cloudflared"]:
            path = shutil.which(name)
            if path:
                return path
        # Check common locations
        common = [
            os.path.expanduser("~\\AppData\\Local\\cloudflared\\cloudflared.exe"),
            os.path.expanduser("~\\AppData\\Roaming\\npm\\cloudflared.cmd"),
            os.path.expanduser("~\\AppData\\Roaming\\npm\\cloudflared.ps1"),
            "C:\\cloudflared\\cloudflared.exe",
            "C:\\Program Files\\cloudflared\\cloudflared.exe",
            os.path.join(os.path.dirname(__file__), "..", "bin", "cloudflared.exe"),
        ]
        for p in common:
            if os.path.exists(p):
                return p
        return None

    def _find_ngrok(self) -> Optional[str]:
        """Find ngrok binary."""
        path = shutil.which("ngrok")
        if path:
            return path
        common = [
            os.path.expanduser("~\\AppData\\Local\\ngrok\\ngrok.exe"),
            "C:\\ngrok\\ngrok.exe",
        ]
        for p in common:
            if os.path.exists(p):
                return p
        return None

    def start_cloudflared(self, port: int) -> dict:
        """Start a Cloudflare quick tunnel (no account needed)."""
        binary = self._find_cloudflared()
        if not binary:
            return {
                "success": False,
                "error": "cloudflared not found. Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/",
                "install_hint": "winget install Cloudflare.cloudflared  OR  choco install cloudflared",
            }

        self.logger.info(f"Starting cloudflared tunnel on port {port}...")
        try:
            self._process = subprocess.Popen(
                [binary, "tunnel", "--url", f"http://localhost:{port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            return {"success": False, "error": f"Failed to start cloudflared: {e}"}

        # Wait for URL in output
        url = self._wait_for_url(timeout=30)
        if url:
            self._tunnel_url = url
            self._running = True
            audit_log(self.settings, "tunnel_started", {"provider": "cloudflared", "url": url})
            return {"success": True, "provider": "cloudflared", "url": url}
        else:
            self.stop()
            return {"success": False, "error": "Timed out waiting for tunnel URL. Check cloudflared output."}

    def start_ngrok(self, port: int) -> dict:
        """Start an ngrok tunnel (free tier, may need auth)."""
        binary = self._find_ngrok()
        if not binary:
            return {
                "success": False,
                "error": "ngrok not found. Install: https://ngrok.com/download",
                "install_hint": "winget install ngrok.ngrok  OR  choco install ngrok",
            }

        self.logger.info(f"Starting ngrok tunnel on port {port}...")
        try:
            self._process = subprocess.Popen(
                [binary, "http", str(port), "--log=stdout"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            return {"success": False, "error": f"Failed to start ngrok: {e}"}

        url = self._wait_for_url_ngrok(timeout=15)
        if url:
            self._tunnel_url = url
            self._running = True
            audit_log(self.settings, "tunnel_started", {"provider": "ngrok", "url": url})
            return {"success": True, "provider": "ngrok", "url": url}
        else:
            self.stop()
            return {"success": False, "error": "Timed out waiting for ngrok URL. You may need to run: ngrok config add-authtoken YOUR_TOKEN"}

    def start(self, port: int) -> dict:
        """Start tunnel using configured provider."""
        provider = self.settings.tunnel_provider.lower()

        if self.settings.tunnel_custom_url:
            self._tunnel_url = self.settings.tunnel_custom_url
            return {"success": True, "provider": "custom", "url": self._tunnel_url}

        if provider == "cloudflared":
            return self.start_cloudflared(port)
        elif provider == "ngrok":
            return self.start_ngrok(port)
        elif provider == "none":
            return {"success": True, "provider": "none", "url": None, "note": "Tunnels disabled. Use local network or custom URL."}
        else:
            return {"success": False, "error": f"Unknown tunnel provider: {provider}"}

    def stop(self):
        """Stop the tunnel."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        self._tunnel_url = None
        self._running = False
        self.logger.info("Tunnel stopped.")

    def _wait_for_url(self, timeout: int = 30) -> Optional[str]:
        """Wait for cloudflared to output a tunnel URL."""
        import select
        deadline = time.time() + timeout
        buffer = ""
        while time.time() < deadline:
            if self._process and self._process.stdout:
                line = self._process.stdout.readline()
                if line:
                    buffer += line
                    self.logger.debug(f"cloudflared: {line.strip()}")
                    # Look for URL pattern
                    match = re.search(r'(https://[a-z0-9-]+\.trycloudflare\.com)', line)
                    if match:
                        return match.group(1)
                    # Also check for errors
                    if "failed to request" in line.lower() or "error" in line.lower():
                        self.logger.warning(f"cloudflared issue: {line.strip()}")
                else:
                    time.sleep(0.2)
            else:
                break
        return None

    def _wait_for_url_ngrok(self, timeout: int = 15) -> Optional[str]:
        """Wait for ngrok to output a tunnel URL."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._process and self._process.stdout:
                line = self._process.stdout.readline()
                if line:
                    self.logger.debug(f"ngrok: {line.strip()}")
                    match = re.search(r'(https://[a-z0-9-]+\.ngrok-free\.app)', line)
                    if not match:
                        match = re.search(r'(https://[a-z0-9-]+\.ngrok\.io)', line)
                    if match:
                        return match.group(1)
                else:
                    time.sleep(0.2)
            else:
                break
        return None

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "provider": self.settings.tunnel_provider,
            "url": self._tunnel_url,
        }
