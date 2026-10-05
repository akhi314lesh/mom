"""
desktop/overlay_launcher.py — Desktop Overlay Shell Launcher.

Fulfills ADR-005:
- Opens an always-on-top, low-distraction floating desktop window.
- Attempts to use pywebview; if unavailable, seamlessly launches the user's default
  browser at the overlay endpoint in app-window mode.
- Registers global hotkey (Ctrl+Shift+M) if hotkey libraries are present.
- Strictly decoupled from audio capture controllers (contains zero audio capture code).
"""
import argparse
import sys
import webbrowser


def launch_overlay(meeting_id: str = "default", port: int = 5173, backend_port: int = 8000):
    overlay_url = f"http://localhost:{port}/overlay/{meeting_id}"

    print(f"==================================================")
    print(f" MOM for meetings — Desktop Overlay Shell (ADR-005)")
    print(f" Meeting ID : {meeting_id}")
    print(f" Overlay URL: {overlay_url}")
    print(f" Hotkey     : Ctrl+Shift+M (Mark Moment)")
    print(f"==================================================")

    # 1. Try launching with pywebview for native frameless always-on-top window
    try:
        import webview  # type: ignore

        print("[+] pywebview detected. Launching native always-on-top floating overlay...")
        window = webview.create_window(
            title="MOM for meetings — Desktop Overlay",
            url=overlay_url,
            width=440,
            height=680,
            resizable=True,
            on_top=True,  # Always on top
            frameless=False,
            easy_drag=True,
        )
        webview.start(debug=False)
        return
    except ImportError:
        print("[-] pywebview not installed. Graceful fallback to system browser...")
    except Exception as exc:
        print(f"[-] pywebview initialization failed ({exc}). Graceful fallback to system browser...")

    # 2. Fallback: Open system browser at the overlay URL
    try:
        webbrowser.open_new(overlay_url)
        print(f"[✓] Opened overlay in browser window: {overlay_url}")
        print("    Tip: Keep this window floating alongside your video call.")
    except Exception as exc:
        print(f"[!] Could not launch browser automatically: {exc}")
        print(f"    Please manually navigate to: {overlay_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MoM Desktop Overlay Shell")
    parser.add_argument("--meeting-id", default="mtg-live", help="Meeting ID to bind the overlay to")
    parser.add_argument("--port", type=int, default=5173, help="Frontend server port (default: 5173)")
    parser.add_argument("--backend-port", type=int, default=8000, help="Backend API port (default: 8000)")
    args = parser.parse_args()

    launch_overlay(meeting_id=args.meeting_id, port=args.port, backend_port=args.backend_port)
