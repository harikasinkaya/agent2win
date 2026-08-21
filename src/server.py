"""
agent2win — Main HTTP/WebSocket Server
The core API server that web & cloud AI agents connect to.
Provides REST endpoints and WebSocket for real-time control.
"""
import asyncio
import json
import time
import base64
import os
import sys
import ctypes
from pathlib import Path
from typing import Optional

try:
    from aiohttp import web
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

from .config import Settings
from .logger import setup_logger, audit_log
from .commands import CommandEngine
from .screen import ScreenCapture
from .input_control import InputController
from .filesystem import FilesystemManager
from .processes import ProcessManager
from .notifications import NotificationManager
from .tunnel import TunnelManager
from .virtual_desktop import VirtualDesktopManager
from .window_manager import WindowManager
from .clipboard import ClipboardManager
from .audio import AudioController
from .system_power import SystemPower
from .network import NetworkManager
from .registry import RegistryManager
from .services import ServicesManager
from .environment import EnvironmentManager


class ArenaServer:
    """Main server that exposes the Windows control API."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.load()
        self.logger = setup_logger(self.settings)

        # Core modules
        self.notifications = NotificationManager(self.settings, self.logger)
        self.commands = CommandEngine(self.settings, self.logger, self.notifications.request_approval)
        self.screen = ScreenCapture(self.settings, self.logger)
        self.input = InputController(self.settings, self.logger, self.notifications.request_approval)
        self.filesystem = FilesystemManager(self.settings, self.logger, self.notifications.request_approval)
        self.processes = ProcessManager(self.settings, self.logger, self.notifications.request_approval)

        # New modules
        self.tunnel = TunnelManager(self.settings, self.logger)
        self.desktops = VirtualDesktopManager(self.settings, self.logger)
        self.windows = WindowManager(self.settings, self.logger)
        self.clipboard = ClipboardManager(self.settings, self.logger)
        self.audio = AudioController(self.settings, self.logger)
        self.power = SystemPower(self.settings, self.logger, self.notifications.request_approval)
        self.network = NetworkManager(self.settings, self.logger)
        self.registry = RegistryManager(self.settings, self.logger, self.notifications.request_approval)
        self.services = ServicesManager(self.settings, self.logger, self.notifications.request_approval)
        self.environment = EnvironmentManager(self.settings, self.logger, self.notifications.request_approval)

        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._start_time = time.time()

    def _check_auth(self, request: web.Request) -> bool:
        if not self.settings.api_key:
            return True
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:] == self.settings.api_key
        key = request.query.get("key", "")
        return key == self.settings.api_key

    def _json_response(self, data: dict, status: int = 200) -> web.Response:
        # Custom encoder to handle ctypes and other non-serializable objects
        def default_encoder(obj):
            if isinstance(obj, (ctypes.c_long, ctypes.c_int, ctypes.c_ulong, ctypes.c_uint,
                                ctypes.c_longlong, ctypes.c_ulonglong, ctypes.c_short,
                                ctypes.c_ushort, ctypes.c_byte, ctypes.c_ubyte)):
                return int(obj)
            if isinstance(obj, (ctypes.c_float, ctypes.c_double)):
                return float(obj)
            if isinstance(obj, ctypes.POINTER(ctypes.c_int)):
                return int(obj.contents)
            if hasattr(obj, '_type_'):  # ctypes pointer
                return int(obj)
            if hasattr(obj, '__int__'):
                return int(obj)
            return str(obj)

        return web.json_response(data, status=status, content_type="application/json", dumps=lambda o: json.dumps(o, default=default_encoder))

    def _unauthorized(self) -> web.Response:
        return self._json_response({"error": "Unauthorized"}, 401)

    # ─── Index ─────────────────────────────────────────────────────────

    async def handle_index(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        uptime = int(time.time() - self._start_time)
        html = f"""<!DOCTYPE html>
<html><head><title>agent2win API</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',sans-serif;background:#0a0a0f;color:#e0e0e0;padding:30px;max-width:1000px;margin:auto}}
  h1{{color:#00d4ff;font-size:2em;margin-bottom:5px}}
  .sub{{color:#888;margin-bottom:20px}}
  h2{{color:#ff6b6b;margin:25px 0 10px;font-size:1.1em;border-bottom:1px solid #222;padding-bottom:5px}}
  code{{background:#1a1a2e;padding:2px 8px;border-radius:4px;color:#00ff88;font-size:0.9em}}
  .ep{{background:#12121f;border-left:3px solid #00d4ff;padding:10px 14px;margin:6px 0;border-radius:4px;font-size:0.9em}}
  .m{{font-weight:bold;color:#00ff88;min-width:50px;display:inline-block}}
  .badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:0.75em;margin-left:8px}}
  .ok{{background:#00ff8822;color:#00ff88}} .warn{{background:#ff444422;color:#ff4444}}
  .info{{background:#00d4ff11;color:#00d4ff;padding:12px;border-radius:8px;margin:10px 0}}
</style></head><body>
<h1>🚀 agent2win</h1>
<div class="sub">Universal Bridge Between Web/Cloud AI & Windows OS v1.0.0 | Uptime: {uptime}s
<span class="badge {'warn' if self.settings.unrestricted_mode else 'ok'}">{'UNRESTRICTED' if self.settings.unrestricted_mode else 'SECURE'}</span>
</div>

<h2>🖥️ System</h2>
<div class="ep"><span class="m">GET</span> <code>/api/info</code> System info</div>
<div class="ep"><span class="m">GET</span> <code>/api/settings</code> Current settings</div>
<div class="ep"><span class="m">POST</span> <code>/api/settings</code> Update settings</div>

<h2>📸 Screen</h2>
<div class="ep"><span class="m">GET</span> <code>/api/screen</code> Screenshot (base64 JPEG)</div>
<div class="ep"><span class="m">GET</span> <code>/api/screen/info</code> Monitor info</div>

<h2>💻 Commands</h2>
<div class="ep"><span class="m">POST</span> <code>/api/command</code> Execute <code>{{"cmd":"dir"}}</code></div>

<h2>🖱️ Mouse</h2>
<div class="ep"><span class="m">POST</span> <code>/api/mouse/click</code> <code>{{"x":100,"y":200}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/mouse/move</code> <code>{{"x":100,"y":200}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/mouse/scroll</code> <code>{{"clicks":-5}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/mouse/drag</code> <code>{{"x1":0,"y1":0,"x2":100,"y2":100}}</code></div>

<h2>⌨️ Keyboard</h2>
<div class="ep"><span class="m">POST</span> <code>/api/keyboard/type</code> <code>{{"text":"hello"}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/keyboard/press</code> <code>{{"key":"enter"}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/keyboard/hotkey</code> <code>{{"keys":["ctrl","c"]}}</code></div>

<h2>📁 Files</h2>
<div class="ep"><span class="m">GET</span> <code>/api/files/list?path=C:\\</code></div>
<div class="ep"><span class="m">GET</span> <code>/api/files/drives</code></div>
<div class="ep"><span class="m">GET</span> <code>/api/files/read?path=...</code></div>
<div class="ep"><span class="m">GET</span> <code>/api/files/search?dir=...&pattern=*.txt</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/files/write</code> <code>{{"path":"...","content":"..."}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/files/mkdir</code> <code>{{"path":"..."}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/files/delete</code> <code>{{"path":"..."}}</code></div>

<h2>🚀 Processes</h2>
<div class="ep"><span class="m">GET</span> <code>/api/processes</code> List processes</div>
<div class="ep"><span class="m">POST</span> <code>/api/processes/launch</code> <code>{{"path":"app.exe"}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/processes/kill</code> <code>{{"pid":1234}}</code></div>

<h2>🪟 Windows</h2>
<div class="ep"><span class="m">GET</span> <code>/api/windows</code> List all windows</div>
<div class="ep"><span class="m">GET</span> <code>/api/windows/find?title=Chrome</code></div>
<div class="ep"><span class="m">GET</span> <code>/api/windows/foreground</code> Current focused window</div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/focus</code> <code>{{"hwnd":12345}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/focus_by_title</code> <code>{{"title":"Notepad"}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/minimize</code> <code>{{"hwnd":12345}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/maximize</code> <code>{{"hwnd":12345}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/resize</code> <code>{{"hwnd":...,"width":800,"height":600}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/move</code> <code>{{"hwnd":...,"x":0,"y":0}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/geometry</code> <code>{{"hwnd":...,"x":0,"y":0,"width":800,"height":600}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/close</code> <code>{{"hwnd":12345}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/hide</code> <code>{{"hwnd":12345}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/show</code> <code>{{"hwnd":12345}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/screenshot</code> <code>{{"hwnd":12345}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/windows/tile</code> <code>{{"hwnds":[...],"cols":2}}</code></div>

<h2>🖥️ Virtual Desktops</h2>
<div class="ep"><span class="m">GET</span> <code>/api/desktops</code> List desktops</div>
<div class="ep"><span class="m">POST</span> <code>/api/desktops/create</code> <code>{{"name":"Agent"}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/desktops/switch</code> <code>{{"index":2}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/desktops/switch_agent</code> Switch to agent desktop</div>
<div class="ep"><span class="m">POST</span> <code>/api/desktops/switch_user</code> Switch to user desktop</div>
<div class="ep"><span class="m">POST</span> <code>/api/desktops/move_window</code> <code>{{"hwnd":...,"desktop":2}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/desktops/remove</code> <code>{{"index":2}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/desktops/setup</code> One-click agent workspace</div>

<h2>📋 Clipboard</h2>
<div class="ep"><span class="m">GET</span> <code>/api/clipboard</code> Get clipboard text</div>
<div class="ep"><span class="m">POST</span> <code>/api/clipboard</code> <code>{{"text":"hello"}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/clipboard/clear</code></div>

<h2>🔊 Audio</h2>
<div class="ep"><span class="m">GET</span> <code>/api/audio/volume</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/audio/volume</code> <code>{{"level":50}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/audio/mute</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/audio/unmute</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/audio/toggle_mute</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/audio/volume_up</code> <code>{{"step":10}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/audio/volume_down</code> <code>{{"step":10}}</code></div>
<div class="ep"><span class="m">GET</span> <code>/api/audio/devices</code></div>

<h2>🌐 Network</h2>
<div class="ep"><span class="m">GET</span> <code>/api/network/ip</code> Local + public IP</div>
<div class="ep"><span class="m">GET</span> <code>/api/network/wifi</code> WiFi info</div>
<div class="ep"><span class="m">GET</span> <code>/api/network/wifi/list</code> Available networks</div>
<div class="ep"><span class="m">GET</span> <code>/api/network/connections</code> Active connections</div>
<div class="ep"><span class="m">POST</span> <code>/api/network/ping</code> <code>{{"host":"8.8.8.8"}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/network/traceroute</code> <code>{{"host":"google.com"}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/network/nslookup</code> <code>{{"domain":"google.com"}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/network/download</code> <code>{{"url":"...","save_path":"..."}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/network/check_port</code> <code>{{"host":"...","port":80}}</code></div>

<h2>⚡ System Power</h2>
<div class="ep"><span class="m">POST</span> <code>/api/power/lock</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/power/shutdown</code> <code>{{"delay_sec":0}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/power/restart</code> <code>{{"delay_sec":0}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/power/cancel</code> Cancel shutdown</div>
<div class="ep"><span class="m">POST</span> <code>/api/power/sleep</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/power/hibernate</code></div>
<div class="ep"><span class="m">GET</span> <code>/api/power/uptime</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/power/empty_trash</code></div>

<h2>🔧 Services</h2>
<div class="ep"><span class="m">GET</span> <code>/api/services</code> List services</div>
<div class="ep"><span class="m">GET</span> <code>/api/services?filter=spooler</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/services/start</code> <code>{{"name":"..."}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/services/stop</code> <code>{{"name":"..."}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/services/restart</code> <code>{{"name":"..."}}</code></div>

<h2>📋 Registry</h2>
<div class="ep"><span class="m">POST</span> <code>/api/registry/read</code> <code>{{"hive":"HKCU","path":"..."}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/registry/list</code> <code>{{"hive":"HKCU","path":"..."}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/registry/write</code> <code>{{"hive":"HKCU","path":"...","name":"...","value":"..."}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/registry/delete</code> <code>{{"hive":"HKCU","path":"..."}}</code></div>

<h2>🌍 Environment</h2>
<div class="ep"><span class="m">GET</span> <code>/api/env?scope=user</code> Environment variables</div>
<div class="ep"><span class="m">POST</span> <code>/api/env/set</code> <code>{{"name":"...","value":"..."}}</code></div>
<div class="ep"><span class="m">GET</span> <code>/api/env/path</code> PATH entries</div>
<div class="ep"><span class="m">GET</span> <code>/api/programs</code> Installed programs</div>
<div class="ep"><span class="m">GET</span> <code>/api/startup</code> Startup items</div>
<div class="ep"><span class="m">GET</span> <code>/api/tasks</code> Scheduled tasks</div>

<h2>✅ Approvals</h2>
<div class="ep"><span class="m">GET</span> <code>/api/approvals</code> Pending approvals</div>
<div class="ep"><span class="m">POST</span> <code>/api/approvals/approve</code> <code>{{"request_id":"..."}}</code></div>
<div class="ep"><span class="m">POST</span> <code>/api/approvals/deny</code> <code>{{"request_id":"..."}}</code></div>

<h2>🔌 WebSocket</h2>
<div class="info">Connect to <code>ws://HOST:7770/ws</code> — same actions as REST but lower latency.
All actions from REST are available via WebSocket JSON messages.</div>
</body></html>"""
        return web.Response(text=html, content_type="text/html")

    # ─── System ────────────────────────────────────────────────────────

    async def handle_info(self, request):
        if not self._check_auth(request): return self._unauthorized()
        info = await self.processes.get_system_info()
        info["server_uptime_sec"] = int(time.time() - self._start_time)
        info["unrestricted_mode"] = self.settings.unrestricted_mode
        info["tunnel_url"] = self.tunnel.tunnel_url
        info["version"] = "1.0.0"
        return self._json_response(info)

    async def handle_command(self, request):
        if not self._check_auth(request): return self._unauthorized()
        data = await request.json()
        result = await self.commands.execute(data.get("cmd", ""), cwd=data.get("cwd"), timeout=data.get("timeout"))
        return self._json_response(result)

    # ─── Screen ────────────────────────────────────────────────────────

    async def handle_screenshot(self, request):
        if not self._check_auth(request): return self._unauthorized()
        result = self.screen.capture_screen(monitor=int(request.query.get("monitor", "0")))
        return self._json_response(result)

    async def handle_screen_info(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(self.screen.get_screen_info())

    # ─── Mouse ─────────────────────────────────────────────────────────

    async def handle_mouse_click(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.input.mouse_click(d["x"], d["y"], d.get("button", "left"), d.get("clicks", 1)))

    async def handle_mouse_move(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.input.mouse_move(d["x"], d["y"]))

    async def handle_mouse_scroll(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.input.mouse_scroll(d["clicks"], d.get("x"), d.get("y")))

    async def handle_mouse_drag(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.input.mouse_drag(d["x1"], d["y1"], d["x2"], d["y2"]))

    # ─── Keyboard ──────────────────────────────────────────────────────

    async def handle_keyboard_type(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        text = d.get("text", "")
        if d.get("unicode") or not text.isascii():
            return self._json_response(await self.input.type_unicode(text))
        return self._json_response(await self.input.type_text(text, d.get("interval", 0.02)))

    async def handle_keyboard_press(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.input.press_key(d["key"]))

    async def handle_keyboard_hotkey(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.input.hotkey(*d["keys"]))

    # ─── Files ─────────────────────────────────────────────────────────

    async def handle_files_list(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.filesystem.list_dir(request.query.get("path", "C:\\"), request.query.get("hidden", "false").lower() == "true"))

    async def handle_files_read(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.filesystem.read_file(request.query.get("path", ""), int(request.query.get("max_bytes", str(102400)))))

    async def handle_files_write(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.filesystem.write_file(d["path"], d["content"]))

    async def handle_files_delete(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.filesystem.delete_file(d["path"]))

    async def handle_files_mkdir(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.filesystem.create_dir(d["path"]))

    async def handle_files_drives(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.filesystem.get_drives())

    async def handle_files_search(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.filesystem.search_files(request.query.get("dir", "C:\\"), request.query.get("pattern", "*"), int(request.query.get("max", "50"))))

    # ─── Processes ─────────────────────────────────────────────────────

    async def handle_processes_list(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.processes.list_processes(request.query.get("filter")))

    async def handle_processes_launch(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.processes.launch_program(d["path"], d.get("args", ""), d.get("cwd")))

    async def handle_processes_kill(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.processes.kill_process(d["pid"]))

    # ─── Windows ───────────────────────────────────────────────────────

    async def handle_windows_list(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.windows.list_windows())

    async def handle_windows_find(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.windows.find_window(request.query.get("title", "")))

    async def handle_windows_foreground(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.windows.get_foreground_window())

    async def handle_windows_focus(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.focus_window(d["hwnd"]))

    async def handle_windows_focus_title(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.focus_by_title(d["title"]))

    async def handle_windows_minimize(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.minimize_window(d["hwnd"]))

    async def handle_windows_maximize(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.maximize_window(d["hwnd"]))

    async def handle_windows_resize(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.resize_window(d["hwnd"], d["width"], d["height"]))

    async def handle_windows_move(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.move_window(d["hwnd"], d["x"], d["y"]))

    async def handle_windows_geometry(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.set_window_geometry(d["hwnd"], d["x"], d["y"], d["width"], d["height"]))

    async def handle_windows_close(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.close_window(d["hwnd"]))

    async def handle_windows_hide(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.hide_window(d["hwnd"]))

    async def handle_windows_show(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.show_window(d["hwnd"]))

    async def handle_windows_screenshot(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.screenshot_window(d["hwnd"]))

    async def handle_windows_tile(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.windows.tile_windows(d["hwnds"], d.get("cols", 2)))

    # ─── Virtual Desktops ──────────────────────────────────────────────

    async def handle_desktops_list(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.desktops.list_desktops())

    async def handle_desktops_create(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.desktops.create_desktop(d.get("name", "agent2win Agent")))

    async def handle_desktops_switch(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.desktops.switch_to_desktop(d["index"]))

    async def handle_desktops_switch_agent(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.desktops.switch_to_agent_desktop())

    async def handle_desktops_switch_user(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.desktops.switch_to_user_desktop())

    async def handle_desktops_move_window(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.desktops.move_window_to_desktop(d["hwnd"], d["desktop"]))

    async def handle_desktops_remove(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.desktops.remove_desktop(d["index"]))

    async def handle_desktops_setup(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.desktops.setup_agent_workspace())

    # ─── Clipboard ─────────────────────────────────────────────────────

    async def handle_clipboard_get(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.clipboard.get_text())

    async def handle_clipboard_set(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.clipboard.set_text(d["text"]))

    async def handle_clipboard_clear(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.clipboard.clear())

    # ─── Audio ─────────────────────────────────────────────────────────

    async def handle_audio_volume(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.audio.get_volume())

    async def handle_audio_set_volume(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.audio.set_volume(d["level"]))

    async def handle_audio_mute(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.audio.mute())

    async def handle_audio_unmute(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.audio.unmute())

    async def handle_audio_toggle_mute(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.audio.toggle_mute())

    async def handle_audio_volume_up(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.audio.volume_up(d.get("step", 5)))

    async def handle_audio_volume_down(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.audio.volume_down(d.get("step", 5)))

    async def handle_audio_devices(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.audio.list_devices())

    # ─── Network ───────────────────────────────────────────────────────

    async def handle_network_ip(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.network.get_ip())

    async def handle_network_wifi(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.network.get_wifi_info())

    async def handle_network_wifi_list(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.network.list_wifi_networks())

    async def handle_network_connections(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.network.get_connections())

    async def handle_network_ping(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.network.ping(d["host"], d.get("count", 4)))

    async def handle_network_traceroute(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.network.traceroute(d["host"]))

    async def handle_network_nslookup(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.network.nslookup(d["domain"]))

    async def handle_network_download(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.network.download_file(d["url"], d["save_path"]))

    async def handle_network_check_port(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.network.check_port(d["host"], d["port"]))

    # ─── Power ─────────────────────────────────────────────────────────

    async def handle_power_lock(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.power.lock())

    async def handle_power_shutdown(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.power.shutdown(d.get("delay_sec", 0)))

    async def handle_power_restart(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.power.restart(d.get("delay_sec", 0)))

    async def handle_power_cancel(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.power.cancel_shutdown())

    async def handle_power_sleep(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.power.sleep())

    async def handle_power_hibernate(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.power.hibernate())

    async def handle_power_uptime(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.power.get_uptime())

    async def handle_power_trash(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.power.empty_trash())

    # ─── Services ──────────────────────────────────────────────────────

    async def handle_services_list(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.services.list_services(request.query.get("filter")))

    async def handle_services_start(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.services.start_service(d["name"]))

    async def handle_services_stop(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.services.stop_service(d["name"]))

    async def handle_services_restart(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.services.restart_service(d["name"]))

    # ─── Registry ──────────────────────────────────────────────────────

    async def handle_registry_read(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.registry.read_key(d["hive"], d["path"], d.get("name", "")))

    async def handle_registry_list(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.registry.list_subkeys(d["hive"], d["path"]))

    async def handle_registry_write(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.registry.write_key(d["hive"], d["path"], d["name"], d["value"], d.get("type", "string")))

    async def handle_registry_delete(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.registry.delete_key(d["hive"], d["path"], d.get("name", "")))

    # ─── Environment ───────────────────────────────────────────────────

    async def handle_env_get(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.environment.get_env_vars(request.query.get("scope", "user")))

    async def handle_env_set(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        return self._json_response(await self.environment.set_env_var(d["name"], d["value"], d.get("scope", "user")))

    async def handle_env_path(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.environment.get_path())

    async def handle_programs(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.environment.list_installed_programs())

    async def handle_startup(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.environment.list_startup_items())

    async def handle_tasks(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(await self.environment.list_scheduled_tasks())

    # ─── Approvals ─────────────────────────────────────────────────────

    async def handle_approvals_list(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response({"success": True, "pending": self.notifications.get_pending()})

    async def handle_approvals_approve(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        if d.get("request_id"):
            return self._json_response({"success": self.notifications.approve_request(d["request_id"])})
        elif d.get("all"):
            self.notifications.approve_all()
            return self._json_response({"success": True})
        return self._json_response({"error": "Provide request_id or all"}, 400)

    async def handle_approvals_deny(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        if d.get("request_id"):
            return self._json_response({"success": self.notifications.deny_request(d["request_id"])})
        elif d.get("all"):
            self.notifications.deny_all()
            return self._json_response({"success": True})
        return self._json_response({"error": "Provide request_id or all"}, 400)

    # ─── Settings & Tunnel ─────────────────────────────────────────────

    async def handle_settings_get(self, request):
        if not self._check_auth(request): return self._unauthorized()
        from dataclasses import asdict
        return self._json_response(asdict(self.settings))

    async def handle_settings_update(self, request):
        if not self._check_auth(request): return self._unauthorized()
        d = await request.json()
        self.settings.update(**d)
        return self._json_response({"success": True})

    async def handle_tunnel_status(self, request):
        if not self._check_auth(request): return self._unauthorized()
        return self._json_response(self.tunnel.get_status())

    # ─── WebSocket ─────────────────────────────────────────────────────

    async def handle_websocket(self, request):
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        if not self._check_auth(request):
            await ws.send_json({"error": "Unauthorized"})
            await ws.close()
            return ws

        self.logger.info("WebSocket connected")
        await ws.send_json({"type": "connected", "version": "1.0.0"})

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        result = await self._ws_action(data)
                        await ws.send_json(result)
                    except json.JSONDecodeError:
                        await ws.send_json({"error": "Invalid JSON"})
                    except Exception as e:
                        await ws.send_json({"error": str(e)})
                elif msg.type == web.WSMsgType.ERROR:
                    break
        except Exception:
            pass
        self.logger.info("WebSocket disconnected")
        return ws

    async def _ws_action(self, d: dict) -> dict:
        a = d.get("action", "")
        # Core
        if a == "command": return await self.commands.execute(d.get("cmd", ""), d.get("cwd"), d.get("timeout"))
        if a == "screenshot": return self.screen.capture_screen(d.get("monitor", 0))
        if a == "screen_info": return self.screen.get_screen_info()
        # Mouse
        if a == "click": return await self.input.mouse_click(d["x"], d["y"], d.get("button", "left"), d.get("clicks", 1))
        if a == "double_click": return await self.input.mouse_double_click(d["x"], d["y"])
        if a == "right_click": return await self.input.mouse_right_click(d["x"], d["y"])
        if a == "mouse_move": return await self.input.mouse_move(d["x"], d["y"])
        if a == "scroll": return await self.input.mouse_scroll(d["clicks"], d.get("x"), d.get("y"))
        if a == "drag": return await self.input.mouse_drag(d["x1"], d["y1"], d["x2"], d["y2"])
        if a == "mouse_pos": return self.input.get_mouse_position()
        if a == "screen_size": return self.input.get_screen_size()
        # Keyboard
        if a == "type":
            text = d.get("text", "")
            if d.get("unicode") or not text.isascii():
                return await self.input.type_unicode(text)
            return await self.input.type_text(text)
        if a == "press": return await self.input.press_key(d["key"])
        if a == "hotkey": return await self.input.hotkey(*d["keys"])
        if a == "key_down": return await self.input.key_down(d["key"])
        if a == "key_up": return await self.input.key_up(d["key"])
        # Files
        if a == "list_dir": return await self.filesystem.list_dir(d.get("path", "C:\\"), d.get("hidden", False))
        if a == "read_file": return await self.filesystem.read_file(d["path"], d.get("max_bytes", 102400))
        if a == "write_file": return await self.filesystem.write_file(d["path"], d["content"])
        if a == "delete": return await self.filesystem.delete_file(d["path"])
        if a == "mkdir": return await self.filesystem.create_dir(d["path"])
        if a == "drives": return await self.filesystem.get_drives()
        if a == "search": return await self.filesystem.search_files(d.get("dir", "C:\\"), d.get("pattern", "*"), d.get("max", 50))
        if a == "file_info": return await self.filesystem.get_file_info(d["path"])
        # Processes
        if a == "processes": return await self.processes.list_processes(d.get("filter"))
        if a == "launch": return await self.processes.launch_program(d["path"], d.get("args", ""), d.get("cwd"))
        if a == "kill": return await self.processes.kill_process(d["pid"])
        if a == "system_info": return await self.processes.get_system_info()
        # Windows
        if a == "windows": return await self.windows.list_windows()
        if a == "find_window": return await self.windows.find_window(d["title"])
        if a == "foreground": return await self.windows.get_foreground_window()
        if a == "focus": return await self.windows.focus_window(d["hwnd"])
        if a == "focus_title": return await self.windows.focus_by_title(d["title"])
        if a == "minimize": return await self.windows.minimize_window(d["hwnd"])
        if a == "maximize": return await self.windows.maximize_window(d["hwnd"])
        if a == "close_window": return await self.windows.close_window(d["hwnd"])
        if a == "resize": return await self.windows.resize_window(d["hwnd"], d["width"], d["height"])
        if a == "move": return await self.windows.move_window(d["hwnd"], d["x"], d["y"])
        if a == "geometry": return await self.windows.set_window_geometry(d["hwnd"], d["x"], d["y"], d["width"], d["height"])
        if a == "hide": return await self.windows.hide_window(d["hwnd"])
        if a == "show": return await self.windows.show_window(d["hwnd"])
        if a == "screenshot_window": return await self.windows.screenshot_window(d["hwnd"])
        if a == "tile": return await self.windows.tile_windows(d["hwnds"], d.get("cols", 2))
        # Desktops
        if a == "desktops": return await self.desktops.list_desktops()
        if a == "create_desktop": return await self.desktops.create_desktop(d.get("name", "agent2win Agent"))
        if a == "switch_desktop": return await self.desktops.switch_to_desktop(d["index"])
        if a == "switch_agent": return await self.desktops.switch_to_agent_desktop()
        if a == "switch_user": return await self.desktops.switch_to_user_desktop()
        if a == "move_to_desktop": return await self.desktops.move_window_to_desktop(d["hwnd"], d["desktop"])
        if a == "remove_desktop": return await self.desktops.remove_desktop(d["index"])
        if a == "setup_workspace": return await self.desktops.setup_agent_workspace()
        # Clipboard
        if a == "clipboard": return await self.clipboard.get_text()
        if a == "set_clipboard": return await self.clipboard.set_text(d["text"])
        if a == "clear_clipboard": return await self.clipboard.clear()
        # Audio
        if a == "volume": return await self.audio.get_volume()
        if a == "set_volume": return await self.audio.set_volume(d["level"])
        if a == "mute": return await self.audio.mute()
        if a == "unmute": return await self.audio.unmute()
        if a == "toggle_mute": return await self.audio.toggle_mute()
        # Network
        if a == "ip": return await self.network.get_ip()
        if a == "wifi": return await self.network.get_wifi_info()
        if a == "ping": return await self.network.ping(d["host"], d.get("count", 4))
        if a == "connections": return await self.network.get_connections()
        # Power
        if a == "lock": return await self.power.lock()
        if a == "shutdown": return await self.power.shutdown(d.get("delay_sec", 0))
        if a == "restart": return await self.power.restart(d.get("delay_sec", 0))
        if a == "cancel_shutdown": return await self.power.cancel_shutdown()
        if a == "sleep": return await self.power.sleep()
        if a == "uptime": return await self.power.get_uptime()
        # Services
        if a == "services": return await self.services.list_services(d.get("filter"))
        if a == "start_service": return await self.services.start_service(d["name"])
        if a == "stop_service": return await self.services.stop_service(d["name"])
        # Registry
        if a == "reg_read": return await self.registry.read_key(d["hive"], d["path"], d.get("name", ""))
        if a == "reg_list": return await self.registry.list_subkeys(d["hive"], d["path"])
        if a == "reg_write": return await self.registry.write_key(d["hive"], d["path"], d["name"], d["value"], d.get("type", "string"))
        # Environment
        if a == "env": return await self.environment.get_env_vars(d.get("scope", "user"))
        if a == "programs": return await self.environment.list_installed_programs()
        if a == "startup": return await self.environment.list_startup_items()
        if a == "tasks": return await self.environment.list_scheduled_tasks()
        # Approvals
        if a == "approvals": return {"success": True, "pending": self.notifications.get_pending()}
        if a == "approve": return {"success": self.notifications.approve_request(d.get("request_id", ""))}
        if a == "deny": return {"success": self.notifications.deny_request(d.get("request_id", ""))}
        if a == "approve_all": self.notifications.approve_all(); return {"success": True}
        if a == "deny_all": self.notifications.deny_all(); return {"success": True}

        return {"error": f"Unknown action: {a}"}

    # ─── Server Lifecycle ──────────────────────────────────────────────

    def _build_app(self):
        @web.middleware
        async def cors(request, handler):
            if request.method == "OPTIONS":
                r = web.Response()
            else:
                try:
                    r = await handler(request)
                except web.HTTPException as ex:
                    r = ex
            r.headers["Access-Control-Allow-Origin"] = "*"
            r.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return r

        app = web.Application(client_max_size=10 * 1024 * 1024, middlewares=[cors])

        # System
        app.router.add_get("/", self.handle_index)
        app.router.add_get("/api/info", self.handle_info)
        app.router.add_post("/api/command", self.handle_command)
        app.router.add_get("/api/settings", self.handle_settings_get)
        app.router.add_post("/api/settings", self.handle_settings_update)
        app.router.add_get("/api/tunnel", self.handle_tunnel_status)

        # Screen
        app.router.add_get("/api/screen", self.handle_screenshot)
        app.router.add_get("/api/screen/info", self.handle_screen_info)

        # Mouse
        app.router.add_post("/api/mouse/click", self.handle_mouse_click)
        app.router.add_post("/api/mouse/move", self.handle_mouse_move)
        app.router.add_post("/api/mouse/scroll", self.handle_mouse_scroll)
        app.router.add_post("/api/mouse/drag", self.handle_mouse_drag)

        # Keyboard
        app.router.add_post("/api/keyboard/type", self.handle_keyboard_type)
        app.router.add_post("/api/keyboard/press", self.handle_keyboard_press)
        app.router.add_post("/api/keyboard/hotkey", self.handle_keyboard_hotkey)

        # Files
        app.router.add_get("/api/files/list", self.handle_files_list)
        app.router.add_get("/api/files/read", self.handle_files_read)
        app.router.add_post("/api/files/write", self.handle_files_write)
        app.router.add_post("/api/files/delete", self.handle_files_delete)
        app.router.add_post("/api/files/mkdir", self.handle_files_mkdir)
        app.router.add_get("/api/files/drives", self.handle_files_drives)
        app.router.add_get("/api/files/search", self.handle_files_search)

        # Processes
        app.router.add_get("/api/processes", self.handle_processes_list)
        app.router.add_post("/api/processes/launch", self.handle_processes_launch)
        app.router.add_post("/api/processes/kill", self.handle_processes_kill)

        # Windows
        app.router.add_get("/api/windows", self.handle_windows_list)
        app.router.add_get("/api/windows/find", self.handle_windows_find)
        app.router.add_get("/api/windows/foreground", self.handle_windows_foreground)
        app.router.add_post("/api/windows/focus", self.handle_windows_focus)
        app.router.add_post("/api/windows/focus_by_title", self.handle_windows_focus_title)
        app.router.add_post("/api/windows/minimize", self.handle_windows_minimize)
        app.router.add_post("/api/windows/maximize", self.handle_windows_maximize)
        app.router.add_post("/api/windows/resize", self.handle_windows_resize)
        app.router.add_post("/api/windows/move", self.handle_windows_move)
        app.router.add_post("/api/windows/geometry", self.handle_windows_geometry)
        app.router.add_post("/api/windows/close", self.handle_windows_close)
        app.router.add_post("/api/windows/hide", self.handle_windows_hide)
        app.router.add_post("/api/windows/show", self.handle_windows_show)
        app.router.add_post("/api/windows/screenshot", self.handle_windows_screenshot)
        app.router.add_post("/api/windows/tile", self.handle_windows_tile)

        # Virtual Desktops
        app.router.add_get("/api/desktops", self.handle_desktops_list)
        app.router.add_post("/api/desktops/create", self.handle_desktops_create)
        app.router.add_post("/api/desktops/switch", self.handle_desktops_switch)
        app.router.add_post("/api/desktops/switch_agent", self.handle_desktops_switch_agent)
        app.router.add_post("/api/desktops/switch_user", self.handle_desktops_switch_user)
        app.router.add_post("/api/desktops/move_window", self.handle_desktops_move_window)
        app.router.add_post("/api/desktops/remove", self.handle_desktops_remove)
        app.router.add_post("/api/desktops/setup", self.handle_desktops_setup)

        # Clipboard
        app.router.add_get("/api/clipboard", self.handle_clipboard_get)
        app.router.add_post("/api/clipboard", self.handle_clipboard_set)
        app.router.add_post("/api/clipboard/clear", self.handle_clipboard_clear)

        # Audio
        app.router.add_get("/api/audio/volume", self.handle_audio_volume)
        app.router.add_post("/api/audio/volume", self.handle_audio_set_volume)
        app.router.add_post("/api/audio/mute", self.handle_audio_mute)
        app.router.add_post("/api/audio/unmute", self.handle_audio_unmute)
        app.router.add_post("/api/audio/toggle_mute", self.handle_audio_toggle_mute)
        app.router.add_post("/api/audio/volume_up", self.handle_audio_volume_up)
        app.router.add_post("/api/audio/volume_down", self.handle_audio_volume_down)
        app.router.add_get("/api/audio/devices", self.handle_audio_devices)

        # Network
        app.router.add_get("/api/network/ip", self.handle_network_ip)
        app.router.add_get("/api/network/wifi", self.handle_network_wifi)
        app.router.add_get("/api/network/wifi/list", self.handle_network_wifi_list)
        app.router.add_get("/api/network/connections", self.handle_network_connections)
        app.router.add_post("/api/network/ping", self.handle_network_ping)
        app.router.add_post("/api/network/traceroute", self.handle_network_traceroute)
        app.router.add_post("/api/network/nslookup", self.handle_network_nslookup)
        app.router.add_post("/api/network/download", self.handle_network_download)
        app.router.add_post("/api/network/check_port", self.handle_network_check_port)

        # Power
        app.router.add_post("/api/power/lock", self.handle_power_lock)
        app.router.add_post("/api/power/shutdown", self.handle_power_shutdown)
        app.router.add_post("/api/power/restart", self.handle_power_restart)
        app.router.add_post("/api/power/cancel", self.handle_power_cancel)
        app.router.add_post("/api/power/sleep", self.handle_power_sleep)
        app.router.add_post("/api/power/hibernate", self.handle_power_hibernate)
        app.router.add_get("/api/power/uptime", self.handle_power_uptime)
        app.router.add_post("/api/power/empty_trash", self.handle_power_trash)

        # Services
        app.router.add_get("/api/services", self.handle_services_list)
        app.router.add_post("/api/services/start", self.handle_services_start)
        app.router.add_post("/api/services/stop", self.handle_services_stop)
        app.router.add_post("/api/services/restart", self.handle_services_restart)

        # Registry
        app.router.add_post("/api/registry/read", self.handle_registry_read)
        app.router.add_post("/api/registry/list", self.handle_registry_list)
        app.router.add_post("/api/registry/write", self.handle_registry_write)
        app.router.add_post("/api/registry/delete", self.handle_registry_delete)

        # Environment
        app.router.add_get("/api/env", self.handle_env_get)
        app.router.add_post("/api/env/set", self.handle_env_set)
        app.router.add_get("/api/env/path", self.handle_env_path)
        app.router.add_get("/api/programs", self.handle_programs)
        app.router.add_get("/api/startup", self.handle_startup)
        app.router.add_get("/api/tasks", self.handle_tasks)

        # Approvals
        app.router.add_get("/api/approvals", self.handle_approvals_list)
        app.router.add_post("/api/approvals/approve", self.handle_approvals_approve)
        app.router.add_post("/api/approvals/deny", self.handle_approvals_deny)

        # WebSocket
        app.router.add_get("/ws", self.handle_websocket)

        return app

    async def start(self):
        if not HAS_AIOHTTP:
            print("ERROR: aiohttp not installed. Run: pip install aiohttp")
            sys.exit(1)

        self._app = self._build_app()
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.settings.host, self.settings.port)
        await site.start()

        display_host = "127.0.0.1" if self.settings.host in ["0.0.0.0", ""] else self.settings.host
        self.logger.info(f"🚀 Server listening on http://{display_host}:{self.settings.port}")

        if self.settings.tunnel_provider != "none":
            tunnel_result = self.tunnel.start(self.settings.port)
            if tunnel_result.get("success") and tunnel_result.get("url"):
                self.logger.info(f"🌐 Public Tunnel : {tunnel_result['url']}")
            elif not tunnel_result.get("success"):
                self.logger.warning(f"⚠️ Tunnel failed: {tunnel_result.get('error')}")

        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await self.stop()

    async def stop(self):
        self.tunnel.stop()
        if self._runner:
            await self._runner.cleanup()
        self.logger.info("Server stopped.")
