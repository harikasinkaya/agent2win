"""
agent2win — Configuration & Settings Manager
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

CONFIG_DIR = Path(os.environ.get("APPDATA", "~")) / "agent2win"
CONFIG_FILE = CONFIG_DIR / "config.json"

@dataclass
class Settings:
    # Server
    host: str = "0.0.0.0"
    port: int = 7770
    api_key: str = ""
    auto_start: bool = False

    # Security
    unrestricted_mode: bool = False          # True = no approval prompts
    require_approval: bool = True            # Show notification before actions
    approval_timeout_sec: int = 60           # Auto-deny after timeout
    allowed_commands: list = field(default_factory=lambda: ["dir", "cd", "type", "echo", "whoami", "hostname", "ipconfig", "systeminfo", "tasklist", "where"])
    blocked_commands: list = field(default_factory=lambda: ["format", "del /s", "rd /s", "reg delete", "bcdedit"])
    max_command_timeout_sec: int = 30

    # Screen
    screen_capture_fps: int = 2              # Frames per second for live view
    screen_quality: int = 60                 # JPEG quality 1-100
    screen_scale: float = 0.75               # Downscale factor

    # Tunnel
    tunnel_provider: str = "cloudflared"     # cloudflared | ngrok | none
    tunnel_custom_url: str = ""              # If you have your own tunnel

    # Logging
    log_file: str = str(CONFIG_DIR / "agent2win.log")
    log_level: str = "INFO"
    audit_log: str = str(CONFIG_DIR / "audit.jsonl")

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls) -> "Settings":
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                known = {f.name for f in cls.__dataclass_fields__.values()}
                return cls(**{k: v for k, v in data.items() if k in known})
            except Exception:
                pass
        s = cls()
        s.save()
        return s

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.save()
