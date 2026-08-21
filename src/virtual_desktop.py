"""
Windows Arena AI — Virtual Desktop Manager
Create, switch, and manage Windows virtual desktops.
The agent can work on its own desktop while the user watches YouTube on another.

Uses Windows COM interfaces and keyboard shortcuts for virtual desktop control.
"""
import subprocess
import time
import ctypes
import ctypes.wintypes
from typing import Optional, List
from .config import Settings
from .logger import audit_log

try:
    import pyvda
    HAS_PYVDA = True
except ImportError:
    HAS_PYVDA = False


class VirtualDesktopManager:
    """Manage Windows 10/11 virtual desktops."""

    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger
        self._agent_desktop_id: Optional[int] = None
        self._agent_desktop_name: str = "Arena AI Agent"

    async def list_desktops(self) -> dict:
        """List all virtual desktops."""
        audit_log(self.settings, "list_desktops", {})
        if HAS_PYVDA:
            try:
                desktops = pyvda.GetDesktops()
                current = pyvda.GetCurrentDesktop()
                result = []
                for i, desk in enumerate(desktops):
                    result.append({
                        "id": desk.id if hasattr(desk, 'id') else i + 1,
                        "index": i + 1,
                        "name": desk.name if hasattr(desk, 'name') and desk.name else f"Desktop {i + 1}",
                        "is_current": desk.id == current.id if hasattr(desk, 'id') else False,
                        "is_agent": self._agent_desktop_id is not None and hasattr(desk, 'id') and desk.id == self._agent_desktop_id,
                    })
                return {"success": True, "desktops": result, "count": len(result), "current_index": result.index(next(d for d in result if d["is_current"])) + 1 if result else 0}
            except Exception as e:
                return {"success": False, "error": f"pyvda error: {e}", "fallback": True}

        # Fallback: use PowerShell
        return await self._list_desktops_ps()

    async def _list_desktops_ps(self) -> dict:
        """List desktops via PowerShell (fallback)."""
        try:
            # Count desktops via Win+Ctrl+Left/Right navigation
            ps_script = '''
            Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DesktopCount {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
}
"@
            # We can at least detect current desktop
            Write-Output "desktop_count_unknown"
            '''
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"success": True, "note": "Limited info without pyvda. Install: pip install pyvda", "desktops": [], "count": 0}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_desktop(self, name: str = "Arena AI Agent") -> dict:
        """Create a new virtual desktop for the agent."""
        audit_log(self.settings, "create_desktop", {"name": name})
        if HAS_PYVDA:
            try:
                new_desk = pyvda.CreateDesktop()
                if hasattr(new_desk, 'rename') and name:
                    try:
                        new_desk.rename(name)
                    except Exception:
                        pass
                self._agent_desktop_id = new_desk.id if hasattr(new_desk, 'id') else None
                self._agent_desktop_name = name
                self.logger.info(f"Created agent desktop: {name} (id={self._agent_desktop_id})")
                return {"success": True, "desktop_id": self._agent_desktop_id, "name": name}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Fallback: Win+Ctrl+D
        try:
            import pyautogui
            pyautogui.hotkey("win", "ctrl", "d")
            time.sleep(0.5)
            self._agent_desktop_name = name
            return {"success": True, "method": "hotkey", "name": name, "note": "Created via Win+Ctrl+D. Install pyvda for better control."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def switch_to_desktop(self, index: int) -> dict:
        """Switch to a specific virtual desktop by index (1-based)."""
        audit_log(self.settings, "switch_desktop", {"index": index})
        if HAS_PYVDA:
            try:
                desktops = pyvda.GetDesktops()
                if 1 <= index <= len(desktops):
                    desktops[index - 1].Go()
                    return {"success": True, "switched_to": index}
                return {"success": False, "error": f"Desktop {index} not found. Total: {len(desktops)}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Fallback: Win+Ctrl+Left/Right
        try:
            import pyautogui
            # First go to desktop 1
            for _ in range(10):
                pyautogui.hotkey("win", "ctrl", "left")
                time.sleep(0.1)
            # Then go to target
            for _ in range(index - 1):
                pyautogui.hotkey("win", "ctrl", "right")
                time.sleep(0.2)
            return {"success": True, "method": "hotkey", "switched_to": index}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def switch_to_agent_desktop(self) -> dict:
        """Switch to the agent's dedicated desktop."""
        if self._agent_desktop_id and HAS_PYVDA:
            try:
                desktops = pyvda.GetDesktops()
                for i, desk in enumerate(desktops):
                    if hasattr(desk, 'id') and desk.id == self._agent_desktop_id:
                        desk.Go()
                        return {"success": True, "switched_to": i + 1, "name": self._agent_desktop_name}
                return {"success": False, "error": "Agent desktop not found"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "No agent desktop created yet. Call create_desktop first."}

    async def switch_to_user_desktop(self) -> dict:
        """Switch back to the user's desktop (desktop 1)."""
        return await self.switch_to_desktop(1)

    async def move_window_to_desktop(self, hwnd: int, desktop_index: int) -> dict:
        """Move a window to a specific desktop."""
        audit_log(self.settings, "move_window_to_desktop", {"hwnd": hwnd, "desktop": desktop_index})
        if HAS_PYVDA:
            try:
                desktops = pyvda.GetDesktops()
                if 1 <= desktop_index <= len(desktops):
                    pyvda.MoveWindowToDesktop(hwnd, desktops[desktop_index - 1])
                    return {"success": True, "hwnd": hwnd, "moved_to": desktop_index}
                return {"success": False, "error": f"Desktop {desktop_index} not found"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "pyvda not installed. pip install pyvda"}

    async def move_current_window_to_desktop(self, desktop_index: int) -> dict:
        """Move the currently focused window to a specific desktop."""
        try:
            import pyautogui
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if HAS_PYVDA:
                return await self.move_window_to_desktop(hwnd, desktop_index)
            # Fallback: Win+Ctrl+Shift+Right/Left
            # This is tricky without pyvda
            return {"success": False, "error": "Install pyvda for window-to-desktop movement"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def remove_desktop(self, index: int) -> dict:
        """Remove/close a virtual desktop."""
        audit_log(self.settings, "remove_desktop", {"index": index})
        if HAS_PYVDA:
            try:
                desktops = pyvda.GetDesktops()
                if 1 <= index <= len(desktops):
                    if index == 1:
                        return {"success": False, "error": "Cannot remove the primary desktop"}
                    desktops[index - 1].Remove()
                    if self._agent_desktop_id and hasattr(desktops[index - 1], 'id') and desktops[index - 1].id == self._agent_desktop_id:
                        self._agent_desktop_id = None
                    return {"success": True, "removed": index}
                return {"success": False, "error": f"Desktop {index} not found"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "pyvda not installed"}

    async def setup_agent_workspace(self) -> dict:
        """
        One-click setup: create agent desktop, switch to it, launch programs.
        The user stays on their desktop while the agent works in the background.
        """
        audit_log(self.settings, "setup_agent_workspace", {})

        # Step 1: Create desktop
        create_result = await self.create_desktop("Arena AI Agent")
        if not create_result.get("success"):
            return create_result

        time.sleep(0.5)

        # Step 2: Switch to agent desktop
        switch_result = await self.switch_to_agent_desktop()
        if not switch_result.get("success"):
            # Fallback
            switch_result = await self.switch_to_desktop(2)

        time.sleep(0.3)

        # Step 3: Switch user back to their desktop
        await self.switch_to_user_desktop()

        return {
            "success": True,
            "message": "Agent workspace ready! Agent desktop created. User is on Desktop 1, agent works on Desktop 2.",
            "agent_desktop": self._agent_desktop_name,
            "user_desktop": 1,
            "instructions": "Use switch_to_agent_desktop() before doing work, then switch_to_user_desktop() to return the user's view.",
        }
