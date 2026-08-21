# 🤖 Agent Protocol — How to Use agent2win

> **For AI Agents & LLMs (ChatGPT, Gemini, Grok, Claude, LangChain, Custom GPTs, etc.).**  
> Read this protocol to control a Windows PC or Windows Server remotely via REST API.

## Connection

The human gives you a URL like `https://xxxx.trycloudflare.com` or `http://192.168.x.x:7770`.
If API key is set: `Authorization: Bearer <key>` header.

## Quick Start

```
GET /api/info → System info
GET /api/screen → Screenshot (base64 JPEG)
POST /api/command {"cmd":"dir"} → Shell command
```

## 🖥️ Background Work with Virtual Desktops

**This is the key feature.** The agent can work on its own virtual desktop while the user uses their PC normally.

```
1. POST /api/desktops/setup          → Create agent desktop (one-click)
2. POST /api/desktops/switch_agent   → Switch to agent desktop
3. ... do your work here ...
4. POST /api/desktops/switch_user    → Return user to their desktop
```

The user stays on Desktop 1 (YouTube, etc.), agent works on Desktop 2.

## 📸 Screen & Windows

```
GET  /api/screen                     → Full desktop screenshot
GET  /api/screen/info                → Monitor info
GET  /api/windows                    → List all open windows
GET  /api/windows/find?title=Chrome  → Find window by title
GET  /api/windows/foreground         → Current focused window
POST /api/windows/focus {"hwnd":...} → Focus a window
POST /api/windows/screenshot {"hwnd":...} → Screenshot specific window
POST /api/windows/minimize {"hwnd":...}
POST /api/windows/maximize {"hwnd":...}
POST /api/windows/resize {"hwnd":...,"width":800,"height":600}
POST /api/windows/move {"hwnd":...,"x":0,"y":0}
POST /api/windows/geometry {"hwnd":...,"x":0,"y":0,"width":800,"height":600}
POST /api/windows/close {"hwnd":...}
POST /api/windows/hide {"hwnd":...}  → Hide window (still running)
POST /api/windows/show {"hwnd":...}
POST /api/windows/tile {"hwnds":[...],"cols":2} → Tile windows
```

## 🖱️ Mouse

```
POST /api/mouse/click  {"x":100,"y":200,"button":"left","clicks":1}
POST /api/mouse/move   {"x":100,"y":200}
POST /api/mouse/scroll {"clicks":-5}
POST /api/mouse/drag   {"x1":0,"y1":0,"x2":100,"y2":100}
```

## ⌨️ Keyboard

```
POST /api/keyboard/type   {"text":"hello"}
POST /api/keyboard/type   {"text":"Привет","unicode":true}
POST /api/keyboard/press  {"key":"enter"}
POST /api/keyboard/hotkey {"keys":["ctrl","c"]}
```

Keys: enter, tab, escape, backspace, delete, space, up, down, left, right, home, end, f1-f12, win.

## 💻 Commands

```
POST /api/command {"cmd":"dir C:\\"}
POST /api/command {"cmd":"ipconfig","timeout":10}
```

## 📁 Files

```
GET  /api/files/list?path=C:\\Users
GET  /api/files/drives
GET  /api/files/read?path=C:\\file.txt
GET  /api/files/search?dir=C:\\&pattern=*.pdf
POST /api/files/write {"path":"...","content":"..."}
POST /api/files/mkdir {"path":"..."}
POST /api/files/delete {"path":"..."}
```

## 🚀 Processes

```
GET  /api/processes
GET  /api/processes?filter=chrome
POST /api/processes/launch {"path":"notepad.exe"}
POST /api/processes/kill {"pid":1234}
```

## 📋 Clipboard

```
GET  /api/clipboard                  → Get clipboard text
POST /api/clipboard {"text":"hello"} → Set clipboard
POST /api/clipboard/clear            → Clear clipboard
```

## 🔊 Audio

```
GET  /api/audio/volume               → Get volume
POST /api/audio/volume {"level":50}  → Set volume 0-100
POST /api/audio/mute
POST /api/audio/unmute
POST /api/audio/toggle_mute
POST /api/audio/volume_up {"step":10}
POST /api/audio/volume_down {"step":10}
GET  /api/audio/devices
```

## 🌐 Network

```
GET  /api/network/ip                 → Local + public IP
GET  /api/network/wifi               → Current WiFi info
GET  /api/network/wifi/list          → Available networks
GET  /api/network/connections        → Active connections
POST /api/network/ping {"host":"8.8.8.8"}
POST /api/network/traceroute {"host":"google.com"}
POST /api/network/nslookup {"domain":"google.com"}
POST /api/network/download {"url":"...","save_path":"..."}
POST /api/network/check_port {"host":"...","port":80}
```

## ⚡ System Power

```
POST /api/power/lock
POST /api/power/shutdown {"delay_sec":60}
POST /api/power/restart  {"delay_sec":0}
POST /api/power/cancel   → Cancel pending shutdown
POST /api/power/sleep
POST /api/power/hibernate
GET  /api/power/uptime
POST /api/power/empty_trash
```

## 🔧 Services

```
GET  /api/services
GET  /api/services?filter=spooler
POST /api/services/start   {"name":"..."}
POST /api/services/stop    {"name":"..."}
POST /api/services/restart {"name":"..."}
```

## 📋 Registry

```
POST /api/registry/read   {"hive":"HKCU","path":"Software\\...","name":"..."}
POST /api/registry/list   {"hive":"HKCU","path":"Software\\..."}
POST /api/registry/write  {"hive":"HKCU","path":"...","name":"...","value":"...","type":"string"}
POST /api/registry/delete {"hive":"HKCU","path":"...","name":"..."}
```

## 🌍 Environment

```
GET  /api/env?scope=user             → Environment variables
GET  /api/env?scope=system
POST /api/env/set {"name":"...","value":"..."}
GET  /api/env/path                   → PATH entries
GET  /api/programs                   → Installed programs
GET  /api/startup                    → Startup items
GET  /api/tasks                      → Scheduled tasks
```

## ✅ Approvals

```
GET  /api/approvals                  → Pending requests
POST /api/approvals/approve {"request_id":"..."} or {"all":true}
POST /api/approvals/deny    {"request_id":"..."} or {"all":true}
```

## 🔌 WebSocket

Connect: `ws://HOST:7770/ws`

All actions above available as JSON: `{"action":"command","cmd":"dir"}`

## Typical Background Workflow

```
1. GET  /api/info                    → Understand system
2. POST /api/desktops/setup          → Create agent workspace
3. POST /api/desktops/switch_agent   → Go to agent desktop
4. POST /api/processes/launch {"path":"chrome.exe"} → Launch browser
5. GET  /api/screen                  → See what's happening
6. POST /api/mouse/click {...}       → Interact
7. POST /api/keyboard/type {...}     → Type
8. POST /api/command {"cmd":"..."}   → Run commands
9. POST /api/desktops/switch_user    → Return user view
```

## Notes

- Coordinates are pixels from top-left (0,0)
- Screenshots are JPEG base64
- Unicode typing uses clipboard (Ctrl+V)
- pyautogui failsafe: move mouse to (0,0) to abort
- All actions logged to audit trail
- Windows paths: `C:\\Users\\...` (double backslash in JSON)
