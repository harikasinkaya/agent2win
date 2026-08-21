# 🚀 agent2win

<div align="center">

### Universal Bridge Between Web / Cloud AI Agents & Windows OS

**Control your Windows PC or Server directly from web-based AI platforms like ChatGPT, Gemini, Grok, Claude, or custom cloud agents.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d4.svg)](https://microsoft.com/windows)
[![API: REST & WebSocket](https://img.shields.io/badge/API-REST%20%26%20WebSocket-green.svg)](#-api-reference-overview)

</div>

---

> 💡 **Turn Any Web AI Into a Windows Agent:**  
> Any AI model or platform with web/API browsing capabilities (**ChatGPT / Custom GPTs**, **Gemini**, **Grok**, **Claude**, **OpenAI Assistants**, **LangChain**, **CrewAI**) can be transformed into an autonomous computer-use agent to control your local Windows PC or remote Windows Server via secure REST / WebSocket endpoints.

---

## 📖 Overview

**agent2win** is a lightweight, high-performance middleware server for Windows. It exposes a unified REST & WebSocket API, instantly accessible over the public internet through automatic Cloudflare or ngrok tunnels with zero router configuration.

Whether you are building custom autonomous agents or connecting conversational web AIs (chatgpt.com, gemini.google.com, grok.com) via Custom Actions / API tools, **agent2win** provides full control over your OS environment.

```
┌──────────────────────────────────────────────────────────────────┐
│ Web & Cloud AI Ecosystem                                         │
│ • chatgpt.com (Custom GPTs / Actions)   • gemini.google.com      │
│ • grok.com / xAI                        • claude.ai / Anthropic  │
│ • Autonomous Frameworks (LangChain, CrewAI, AutoGen, AutoGPT)    │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ HTTPS / WSS (API Key Auth)
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│ Cloudflare / ngrok Public Tunnel (Zero Port-Forwarding)          │
└─────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│ agent2win Server (:7770)                                         │
├─────────────────────────────────┬────────────────────────────────┤
│ • Screen & Window Capture       │ • Mouse & Keyboard Emulation   │
│ • Shell & Command Runner        │ • Virtual Desktop Isolation    │
│ • Filesystem & Registry         │ • Process & Service Manager    │
│ • Clipboard & Audio Controls    │ • Security & Approval Layer    │
└─────────────────────────────────┴────────────────────────────────┘
```

---

## ✨ Key Features

- 🌐 **Web AI Compatibility**: Turn web-based models (**ChatGPT Actions**, **Gemini**, **Grok**, **Claude**) into remote operators for your Windows machines.
- ⚡ **Zero-Config Public Tunnel**: Instant public HTTPS endpoint generated automatically using Cloudflare Tunnel (`cloudflared`) or `ngrok`. No static IP or port forwarding required.
- 🖥️ **Virtual Desktop Isolation**: Create dedicated hidden/secondary virtual desktops (`/api/desktops`). The agent works autonomously on Desktop 2 without interfering with your active tasks on Desktop 1.
- 📸 **Vision & Window Capture**: Full display screenshots or targeted window-handle (`hwnd`) captures in base64 format for visual reasoning.
- 🖱️ **Hardware Input Emulation**: Mouse click, drag, scroll, and keyboard typing with complete Unicode / international character support.
- 💻 **OS & System Administration**: Run PowerShell/CMD scripts, manage filesystem (read/write/search), list/kill processes, inspect Windows Services, and edit Registry keys.
- 🔒 **Comprehensive Security Layer**: Token authentication (`Bearer`), real-time desktop approval prompts for risky commands, system tray killswitch, and audit logging.

---

## ⚡ Quick Start

### 1. Install

Clone repository and install dependencies:

```bash
git clone https://github.com/harikasinkaya/agent2win.git
cd agent2win
pip install -r requirements.txt
```

*Or double-click `install.bat` on Windows.*

### 2. Run Server

```bash
python main.py
```

*Or double-click `start.bat`.*

### 3. Connect Any AI Agent

The console displays your live public HTTPS tunnel:

```text
🌐 Tunnel: https://xxxx-xxxx-xxxx.trycloudflare.com
```

Connect your AI agent (e.g. ChatGPT Custom Action schema, LangChain tool, or web agent) using this URL.

---

## 🤖 Using With Web AIs (ChatGPT, Gemini, Grok, Claude)

### 📋 Direct Prompt to Connect Any Web AI
Copy and paste this prompt directly into **ChatGPT, Gemini, Grok, Claude, or any web AI with browsing/fetching capabilities**:

```markdown
Read the official agent2win control protocol from this URL:
https://raw.githubusercontent.com/harikasinkaya/agent2win/refs/heads/main/AGENT_PROTOCOL.md

You are now an autonomous Windows controller agent.
My agent2win server URL is: <PASTE_YOUR_TUNNEL_URL_HERE>
My API key is: <PASTE_YOUR_API_KEY_OR_LEAVE_EMPTY>

Please inspect the system info, capture the screen, and follow my instructions to control my Windows machine.
```

### ChatGPT Custom GPTs / Actions
1. Open ChatGPT -> Create a GPT -> Configure -> **Add Action**.
2. Set Server URL to your tunnel address (`https://xxxx.trycloudflare.com`).
3. Set Authentication to **API Key** (Bearer token) if configured.
4. Import endpoints from `AGENT_PROTOCOL.md` to let ChatGPT inspect your screen, run commands, and click UI elements.

### Gemini, Grok & Cloud Agents
Pass the public tunnel URL and API endpoints into your agent execution loop. The agent can take screenshots (`/api/screen`), process images with vision models, and issue input commands (`/api/mouse/click`, `/api/keyboard/type`).

---

## 🛠️ CLI Options

| Flag | Description |
|---|---|
| `--port <PORT>` | Server port (Default: `7770`) |
| `--host <IP>` | Bind IP address (Default: `0.0.0.0`) |
| `--key <SECRET>` | Set Bearer token for API authentication |
| `--unrestricted` | Disable action approval prompts (⚠️ use carefully) |
| `--tunnel <PROVIDER>` | Tunnel provider (`cloudflared` or `ngrok`) |
| `--no-tunnel` | Local-only mode (disables tunnels) |
| `--no-tray` | Disable Windows system tray icon |
| `--settings` | Open graphical configuration GUI |

---

## 📡 API Reference Overview

Full protocol specifications available in [AGENT_PROTOCOL.md](AGENT_PROTOCOL.md).

### 🖥️ Virtual Desktops (Background Mode)
- `POST /api/desktops/setup` — Create agent virtual desktop.
- `POST /api/desktops/switch_agent` — Switch active view to agent desktop.
- `POST /api/desktops/switch_user` — Switch active view back to user desktop.

### 📸 Screen & Windows
- `GET /api/screen` — Full desktop screenshot (Base64 JPEG).
- `GET /api/windows` — List active windows with handles (`hwnd`) and coordinates.
- `POST /api/windows/screenshot` — Capture specific window by `hwnd`.
- `POST /api/windows/focus` — Bring window to foreground.

### 🖱️ Mouse & Keyboard
- `POST /api/mouse/click` — `{"x": 500, "y": 300, "button": "left"}`
- `POST /api/mouse/scroll` — `{"clicks": -5}`
- `POST /api/keyboard/type` — `{"text": "Hello World", "unicode": true}`
- `POST /api/keyboard/hotkey` — `{"keys": ["ctrl", "c"]}`

### 💻 Shell & Filesystem
- `POST /api/command` — `{"cmd": "dir C:\\", "timeout": 10}`
- `GET /api/fs/list?path=C:\` — List directory contents.
- `POST /api/fs/read` — Read file contents.
- `POST /api/fs/write` — Write file contents.

---

## 🔒 Security & Approvals

- **Safe Mode (Default)**: Critical actions (destructive shell commands, file deletions, registry writes, system reboot/shutdown) trigger desktop approval prompts.
- **Unrestricted Mode (`--unrestricted`)**: Disables interactive confirmation for headless/autonomous agents.
- **Audit Logs**: All executions recorded in `logs/audit.log`.
- **Tray Killswitch**: Pause or stop the server directly from the Windows taskbar.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
