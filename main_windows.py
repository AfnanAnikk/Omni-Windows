import os
import sys
import argparse
import webview
from omni.config import Config
from omni.windows.app import WindowsAppCoordinator
from omni.windows.ui import HUD_HTML, INDICATOR_HTML

def setup_wizard():
    print("\n" + "=" * 55)
    print("Omni Setup (Windows)")
    print("=" * 55)
    print("Hold Ctrl + 0 to speak your question, release to get answers on your screen.\n")

    api_key = input("Enter your Google Gemini API Key (or press Enter to skip): ").strip()
    if api_key:
        Config.save_api_key(api_key)
        print("Saved GEMINI_API_KEY successfully!\n")

def main():
    parser = argparse.ArgumentParser(description="Omni: Ambient Desktop AI Agent for Windows")
    parser.add_argument("--setup", action="store_true", help="Run interactive configuration setup")
    parser.add_argument("--test-screen", action="store_true", help="Test screen capture and exit")
    args = parser.parse_args()

    if args.test_screen:
        from omni.windows.screen import WindowsScreenCapture
        print("Testing screenshot capture...")
        p = WindowsScreenCapture.capture()
        print(f"Screenshot captured: {p} ({p.stat().st_size} bytes)")
        return

    if args.setup:
        setup_wizard()
    elif not Config.GEMINI_API_KEY and sys.stdin.isatty():
        setup_wizard()

    coordinator = WindowsAppCoordinator()

    # Calculate optimal screen positions
    try:
        import ctypes
        user32 = ctypes.windll.user32
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
    except Exception:
        screen_w, screen_h = 1920, 1080

    hud_w, hud_h = 720, 480
    hud_x = max(0, (screen_w - hud_w) // 2)
    hud_y = max(0, int(screen_h * 0.14))

    ind_w, ind_h = 140, 42
    ind_x = max(0, screen_w - ind_w - 24)
    ind_y = 24

    # 1. Create HUD window (hidden initially, centered in upper-third)
    hud_window = webview.create_window(
        title="Omni",
        html=HUD_HTML,
        width=hud_w,
        height=hud_h,
        x=hud_x,
        y=hud_y,
        frameless=True,
        on_top=True,
        transparent=True,
        js_api=coordinator.api_bridge,
        hidden=True
    )
    coordinator.hud.window = hud_window

    # 2. Create Indicator pill window (hidden initially, anchored top-right)
    indicator_window = webview.create_window(
        title="OmniIndicator",
        html=INDICATOR_HTML,
        width=ind_w,
        height=ind_h,
        x=ind_x,
        y=ind_y,
        frameless=True,
        on_top=True,
        transparent=True,
        hidden=True
    )
    coordinator.indicator.window = indicator_window

    def on_ready():
        coordinator.start()

    # Start Edge Chromium WebView2 event loop
    webview.start(on_ready, gui='edgechromium', debug=False)

if __name__ == "__main__":
    main()
