"""
agent2win — Network Manager
WiFi control, network info, ping, port scanning, downloads.
"""
import subprocess
import socket
import urllib.request
import os
from typing import Optional
from .config import Settings
from .logger import audit_log


class NetworkManager:
    """Network operations and information."""

    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger

    async def get_ip(self) -> dict:
        """Get local and public IP addresses."""
        audit_log(self.settings, "get_ip", {})
        result = {"success": True}

        # Local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            result["local_ip"] = s.getsockname()[0]
            s.close()
        except Exception:
            result["local_ip"] = "unknown"

        # Public IP
        try:
            req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "WindowsArenaAI/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                result["public_ip"] = resp.read().decode().strip()
        except Exception:
            result["public_ip"] = "unknown"

        return result

    async def get_wifi_info(self) -> dict:
        """Get current WiFi connection info."""
        audit_log(self.settings, "get_wifi_info", {})
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            info = {}
            for line in result.stdout.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if "SSID" in key and "BSSID" not in key:
                        info["ssid"] = val
                    elif "State" in key:
                        info["state"] = val
                    elif "Signal" in key:
                        info["signal"] = val
                    elif "Radio type" in key:
                        info["radio_type"] = val
                    elif "Receive rate" in key:
                        info["receive_rate"] = val
                    elif "Transmit rate" in key:
                        info["transmit_rate"] = val
                    elif "Channel" in key:
                        info["channel"] = val
                    elif "Authentication" in key:
                        info["authentication"] = val
            return {"success": True, "wifi": info}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_wifi_networks(self) -> dict:
        """List available WiFi networks."""
        audit_log(self.settings, "list_wifi_networks", {})
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks"],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            networks = []
            current = {}
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    if current:
                        networks.append(current)
                    current = {"ssid": line.split(":", 1)[1].strip() if ":" in line else ""}
                elif ":" in line and current:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if "Network type" in key:
                        current["type"] = val
                    elif "Authentication" in key:
                        current["auth"] = val
                    elif "Encryption" in key:
                        current["encryption"] = val
                    elif "Signal" in key:
                        current["signal"] = val
            if current:
                networks.append(current)
            return {"success": True, "networks": networks, "count": len(networks)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def ping(self, host: str, count: int = 4) -> dict:
        """Ping a host."""
        audit_log(self.settings, "ping", {"host": host, "count": count})
        try:
            result = subprocess.run(
                ["ping", "-n", str(count), host],
                capture_output=True, text=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "host": host, "output": result.stdout, "returncode": result.returncode}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def traceroute(self, host: str) -> dict:
        """Traceroute to a host."""
        audit_log(self.settings, "traceroute", {"host": host})
        try:
            result = subprocess.run(
                ["tracert", "-d", host],
                capture_output=True, text=True, timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "host": host, "output": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def nslookup(self, domain: str) -> dict:
        """DNS lookup."""
        audit_log(self.settings, "nslookup", {"domain": domain})
        try:
            result = subprocess.run(
                ["nslookup", domain],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "domain": domain, "output": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_connections(self) -> dict:
        """List active network connections."""
        audit_log(self.settings, "get_connections", {})
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            connections = []
            for line in result.stdout.split("\n")[4:]:  # Skip headers
                parts = line.split()
                if len(parts) >= 4:
                    connections.append({
                        "protocol": parts[0],
                        "local": parts[1],
                        "remote": parts[2],
                        "state": parts[3] if len(parts) > 3 else "",
                        "pid": parts[-1] if parts[-1].isdigit() else "",
                    })
            return {"success": True, "connections": connections[:100], "total": len(connections)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def download_file(self, url: str, save_path: str) -> dict:
        """Download a file from URL."""
        audit_log(self.settings, "download_file", {"url": url, "path": save_path})
        try:
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            urllib.request.urlretrieve(url, save_path)
            size = os.path.getsize(save_path)
            return {"success": True, "path": save_path, "size_bytes": size}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def check_port(self, host: str, port: int, timeout: float = 3) -> dict:
        """Check if a port is open on a host."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            s.close()
            return {"success": True, "host": host, "port": port, "open": result == 0}
        except Exception as e:
            return {"success": False, "error": str(e)}
