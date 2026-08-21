"""
agent2win — Settings GUI
A simple tkinter-based settings window for configuring the middleware.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, Callable

from .config import Settings


class SettingsGUI:
    """Settings window for Windows Arena AI."""

    def __init__(self, settings: Settings, on_save: Optional[Callable] = None):
        self.settings = settings
        self.on_save = on_save
        self._root: Optional[tk.Tk] = None
        self._vars: dict = {}

    def show(self):
        """Show the settings window in a separate thread."""
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        self._root = tk.Tk()
        self._root.title("agent2win — Settings")
        self._root.geometry("520x680")
        self._root.resizable(False, False)
        self._root.configure(bg="#0a0a0f")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#0a0a0f")
        style.configure("TLabel", background="#0a0a0f", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background="#0a0a0f", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#00d4ff", background="#0a0a0f")
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground="#ff6b6b", background="#0a0a0f")

        main = ttk.Frame(self._root, padding=20)
        main.pack(fill="both", expand=True)

        # Header
        ttk.Label(main, text="🪟 Windows Arena AI Settings", style="Header.TLabel").pack(anchor="w", pady=(0, 15))

        # ── Security Section ──
        ttk.Label(main, text="🔒 Security", style="Section.TLabel").pack(anchor="w", pady=(10, 5))

        self._vars["unrestricted_mode"] = tk.BooleanVar(value=self.settings.unrestricted_mode)
        cb = ttk.Checkbutton(main, text="Unrestricted Mode (no approval prompts)", variable=self._vars["unrestricted_mode"])
        cb.pack(anchor="w", padx=10)

        self._vars["require_approval"] = tk.BooleanVar(value=self.settings.require_approval)
        ttk.Checkbutton(main, text="Require approval for non-read actions", variable=self._vars["require_approval"]).pack(anchor="w", padx=10)

        frame_timeout = ttk.Frame(main)
        frame_timeout.pack(anchor="w", padx=10, pady=5)
        ttk.Label(frame_timeout, text="Approval timeout (sec):").pack(side="left")
        self._vars["approval_timeout_sec"] = tk.IntVar(value=self.settings.approval_timeout_sec)
        ttk.Spinbox(frame_timeout, from_=10, to=300, textvariable=self._vars["approval_timeout_sec"], width=6).pack(side="left", padx=5)

        self._vars["api_key"] = tk.StringVar(value=self.settings.api_key)
        frame_key = ttk.Frame(main)
        frame_key.pack(anchor="w", padx=10, pady=5, fill="x")
        ttk.Label(frame_key, text="API Key:").pack(side="left")
        ttk.Entry(frame_key, textvariable=self._vars["api_key"], width=30, show="*").pack(side="left", padx=5)

        # ── Server Section ──
        ttk.Label(main, text="🌐 Server", style="Section.TLabel").pack(anchor="w", pady=(15, 5))

        frame_port = ttk.Frame(main)
        frame_port.pack(anchor="w", padx=10, pady=5)
        ttk.Label(frame_port, text="Port:").pack(side="left")
        self._vars["port"] = tk.IntVar(value=self.settings.port)
        ttk.Spinbox(frame_port, from_=1024, to=65535, textvariable=self._vars["port"], width=6).pack(side="left", padx=5)

        self._vars["auto_start"] = tk.BooleanVar(value=self.settings.auto_start)
        ttk.Checkbutton(main, text="Auto-start on Windows login", variable=self._vars["auto_start"]).pack(anchor="w", padx=10)

        # ── Tunnel Section ──
        ttk.Label(main, text="🌐 Tunnel", style="Section.TLabel").pack(anchor="w", pady=(15, 5))

        self._vars["tunnel_provider"] = tk.StringVar(value=self.settings.tunnel_provider)
        frame_tunnel = ttk.Frame(main)
        frame_tunnel.pack(anchor="w", padx=10, pady=5)
        for provider in [("cloudflared", "Cloudflare Tunnel"), ("ngrok", "ngrok"), ("none", "Disabled")]:
            ttk.Radiobutton(frame_tunnel, text=provider[1], value=provider[0], variable=self._vars["tunnel_provider"]).pack(anchor="w")

        self._vars["tunnel_custom_url"] = tk.StringVar(value=self.settings.tunnel_custom_url)
        frame_custom = ttk.Frame(main)
        frame_custom.pack(anchor="w", padx=10, pady=5, fill="x")
        ttk.Label(frame_custom, text="Custom URL:").pack(side="left")
        ttk.Entry(frame_custom, textvariable=self._vars["tunnel_custom_url"], width=35).pack(side="left", padx=5)

        # ── Screen Section ──
        ttk.Label(main, text="🖥️ Screen Capture", style="Section.TLabel").pack(anchor="w", pady=(15, 5))

        frame_screen = ttk.Frame(main)
        frame_screen.pack(anchor="w", padx=10, pady=5)
        ttk.Label(frame_screen, text="Quality (1-100):").pack(side="left")
        self._vars["screen_quality"] = tk.IntVar(value=self.settings.screen_quality)
        ttk.Spinbox(frame_screen, from_=10, to=100, textvariable=self._vars["screen_quality"], width=5).pack(side="left", padx=5)
        ttk.Label(frame_screen, text="Scale:").pack(side="left", padx=(15, 0))
        self._vars["screen_scale"] = tk.DoubleVar(value=self.settings.screen_scale)
        ttk.Spinbox(frame_screen, from_=0.25, to=1.0, increment=0.25, textvariable=self._vars["screen_scale"], width=5).pack(side="left", padx=5)

        # ── Buttons ──
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(25, 0))

        ttk.Button(btn_frame, text="💾 Save", command=self._save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="❌ Cancel", command=self._cancel).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Reset Defaults", command=self._reset).pack(side="right", padx=5)

        self._root.mainloop()

    def _save(self):
        for key, var in self._vars.items():
            try:
                value = var.get()
                setattr(self.settings, key, value)
            except Exception:
                pass
        self.settings.save()
        if self.on_save:
            self.on_save(self.settings)
        messagebox.showinfo("Saved", "Settings saved successfully!\nSome changes may require a restart.")
        self._root.destroy()

    def _cancel(self):
        self._root.destroy()

    def _reset(self):
        if messagebox.askyesno("Reset", "Reset all settings to defaults?"):
            default = Settings()
            for key, var in self._vars.items():
                if hasattr(default, key):
                    var.set(getattr(default, key))
