"""
agent2win — Entry Point
Run this to start the middleware server.

Usage:
    python main.py                    # Start with defaults
    python main.py --port 8080        # Custom port
    python main.py --unrestricted     # Enable unrestricted mode
    python main.py --no-tray          # Skip system tray
    python main.py --settings         # Open settings GUI
    python main.py --key mysecretkey  # Set API key
"""
import asyncio
import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Settings
from src.server import ArenaServer
from src.tray import TrayApp
from src.gui import SettingsGUI


def parse_args():
    parser = argparse.ArgumentParser(
        description="agent2win — Universal Bridge Between Web/Cloud AI Agents & Windows OS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          Start server on port 7770
  python main.py --port 8080 --key abc    Custom port with API key
  python main.py --unrestricted           No approval prompts (⚠️ use carefully)
  python main.py --settings               Open settings GUI
  python main.py --tunnel cloudflared     Use Cloudflare tunnel
  python main.py --tunnel ngrok           Use ngrok tunnel
  python main.py --no-tunnel              Disable tunnels
        """,
    )
    parser.add_argument("--port", type=int, help="Server port (default: 7770)")
    parser.add_argument("--host", type=str, help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--key", type=str, help="API key for authentication")
    parser.add_argument("--unrestricted", action="store_true", help="Enable unrestricted mode (no approval prompts)")
    parser.add_argument("--no-tray", action="store_true", help="Don't show system tray icon")
    parser.add_argument("--no-tunnel", action="store_true", help="Disable tunnel")
    parser.add_argument("--tunnel", type=str, choices=["cloudflared", "ngrok"], help="Tunnel provider")
    parser.add_argument("--settings", action="store_true", help="Open settings GUI and exit")
    parser.add_argument("--config", type=str, help="Path to config file")
    return parser.parse_args()


def main():
    args = parse_args()

    # Load settings
    settings = Settings.load()

    # Apply CLI overrides (do not permanently mutate default config unless requested)
    if args.port:
        settings.port = args.port
    if args.host:
        settings.host = args.host
    if args.key:
        settings.api_key = args.key
    if args.unrestricted:
        settings.unrestricted_mode = True
    if args.no_tunnel:
        settings.tunnel_provider = "none"
    elif args.tunnel:
        settings.tunnel_provider = args.tunnel
    elif not settings.tunnel_provider or settings.tunnel_provider == "none":
        # Default to cloudflared unless user explicitly said --no-tunnel
        settings.tunnel_provider = "cloudflared"

    # Settings GUI mode
    if args.settings:
        gui = SettingsGUI(settings)
        gui.show()
        return

    # Clear terminal screen
    os.system("cls" if os.name == "nt" else "clear")

    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    mode_str = f"{YELLOW}UNRESTRICTED (No prompts){RESET}" if settings.unrestricted_mode else f"{GREEN}SECURE (Approval on){RESET}"
    auth_str = f"{GREEN}Enabled (Bearer token){RESET}" if settings.api_key else f"{GRAY}Disabled (Open){RESET}"
    tray_str = f"{GREEN}Active{RESET}" if not args.no_tray else f"{GRAY}Disabled{RESET}"

    # Display host (127.0.0.1 for display clarity)
    display_host = "127.0.0.1" if settings.host in ["0.0.0.0", ""] else settings.host

    banner = f"""{CYAN}{BOLD}
 █████╗  ██████╗ ███████╗███╗   ██╗████████╗██████╗ ██╗    ██╗██╗███╗   ██╗
██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝╚════██╗██║    ██║██║████╗  ██║
███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║    █████╔╝██║ █╗ ██║██║██╔██╗ ██║
██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██╔═══╝ ██║███╗██║██║██║╚██╗██║
██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ███████╗╚███╔███╔╝██║██║ ╚████║
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝ ╚══╝╚══╝ ╚═╝╚═╝  ╚═══╝
{RESET}{GRAY} Universal Bridge Between Web/Cloud AI Agents & Windows OS  {CYAN}v1.0.6{RESET}
{GRAY}───────────────────────────────────────────────────────────────────────────────{RESET}
  {BOLD}Local Endpoint :{RESET} {CYAN}http://{display_host}:{settings.port}{RESET}
  {BOLD}Authentication :{RESET} {auth_str}
  {BOLD}Security Mode  :{RESET} {mode_str}
  {BOLD}System Tray    :{RESET} {tray_str}
  {BOLD}Tunnel Provider:{RESET} {settings.tunnel_provider}
{GRAY}───────────────────────────────────────────────────────────────────────────────{RESET}
  {GRAY}* Press {YELLOW}Ctrl+C{GRAY} in terminal to gracefully shutdown{RESET}
"""
    print(banner)

    # Create server first so we can pass notifications to tray
    server = ArenaServer(settings)

    # Start system tray
    tray = None
    if not args.no_tray:
        try:
            tray = TrayApp(settings, server.notifications, settings.port)
            tray.start()
        except Exception as e:
            pass

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}👋 agent2win shutting down...{RESET}")
    finally:
        if tray:
            tray.stop()


if __name__ == "__main__":
    main()
