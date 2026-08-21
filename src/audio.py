"""
agent2win — Audio Control
Control system volume, mute, and audio devices.
"""
import subprocess
import ctypes
from typing import Optional
from .config import Settings
from .logger import audit_log

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL, CoCreateInstance
    from ctypes import POINTER
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False


class AudioController:
    """System audio control."""

    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger
        self._volume_interface = None

    def _get_volume_interface(self):
        if self._volume_interface is None and HAS_PYCAW:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self._volume_interface = interface.QueryInterface(POINTER(IAudioEndpointVolume))
            except Exception:
                pass
        return self._volume_interface

    async def get_volume(self) -> dict:
        """Get current system volume (0-100)."""
        audit_log(self.settings, "get_volume", {})
        if HAS_PYCAW:
            try:
                vol = self._get_volume_interface()
                if vol:
                    level = vol.GetMasterVolumeLevelScalar()
                    muted = vol.GetMute()
                    return {"success": True, "volume": round(level * 100), "muted": bool(muted), "level_scalar": round(level, 3)}
            except Exception as e:
                pass

        # Fallback: nircmd or PowerShell
        try:
            result = subprocess.run(
                ["powershell", "-command",
                 "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('')"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "note": "Install pycaw for precise volume control: pip install pycaw"}
        except Exception:
            return {"success": False, "error": "Install pycaw: pip install pycaw"}

    async def set_volume(self, level: int) -> dict:
        """Set system volume (0-100)."""
        audit_log(self.settings, "set_volume", {"level": level})
        level = max(0, min(100, level))

        if HAS_PYCAW:
            try:
                vol = self._get_volume_interface()
                if vol:
                    vol.SetMasterVolumeLevelScalar(level / 100.0, None)
                    return {"success": True, "volume": level}
            except Exception:
                pass

        # Fallback: nircmd
        try:
            vol_val = int(level * 65535 / 100)
            subprocess.run(
                ["nircmd", "setsysvolume", str(vol_val)],
                capture_output=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "volume": level, "method": "nircmd"}
        except Exception:
            return {"success": False, "error": "Install pycaw: pip install pycaw"}

    async def mute(self) -> dict:
        """Mute system audio."""
        audit_log(self.settings, "mute", {})
        if HAS_PYCAW:
            try:
                vol = self._get_volume_interface()
                if vol:
                    vol.SetMute(True, None)
                    return {"success": True, "muted": True}
            except Exception:
                pass
        return {"success": False, "error": "Install pycaw: pip install pycaw"}

    async def unmute(self) -> dict:
        """Unmute system audio."""
        audit_log(self.settings, "unmute", {})
        if HAS_PYCAW:
            try:
                vol = self._get_volume_interface()
                if vol:
                    vol.SetMute(False, None)
                    return {"success": True, "muted": False}
            except Exception:
                pass
        return {"success": False, "error": "Install pycaw: pip install pycaw"}

    async def toggle_mute(self) -> dict:
        """Toggle mute state."""
        if HAS_PYCAW:
            try:
                vol = self._get_volume_interface()
                if vol:
                    current = vol.GetMute()
                    vol.SetMute(not current, None)
                    return {"success": True, "muted": not bool(current)}
            except Exception:
                pass
        return {"success": False, "error": "Install pycaw: pip install pycaw"}

    async def volume_up(self, step: int = 5) -> dict:
        """Increase volume by step."""
        current = await self.get_volume()
        if current.get("success"):
            new_level = min(100, current["volume"] + step)
            return await self.set_volume(new_level)
        return current

    async def volume_down(self, step: int = 5) -> dict:
        """Decrease volume by step."""
        current = await self.get_volume()
        if current.get("success"):
            new_level = max(0, current["volume"] - step)
            return await self.set_volume(new_level)
        return current

    async def list_devices(self) -> dict:
        """List audio devices."""
        audit_log(self.settings, "list_audio_devices", {})
        if HAS_PYCAW:
            try:
                devices = AudioUtilities.GetAllDevices()
                result = []
                for d in devices:
                    result.append({
                        "id": str(d.id) if d.id else "",
                        "name": str(d.FriendlyName) if d.FriendlyName else "",
                        "state": str(d.State) if d.State else "",
                    })
                return {"success": True, "devices": result, "count": len(result)}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Install pycaw: pip install pycaw"}
