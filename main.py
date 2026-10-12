import argparse
import sys
import os
import getpass
from pathlib import Path

if sys.platform == "win32":
    import main_windows
    if __name__ == "__main__":
        main_windows.main()
    sys.exit(0)

import AppKit
from PyObjCTools import AppHelper

from omni.config import Config
from omni.app import AppCoordinator

def setup_wizard():
    print("\n" + "=" * 55)
    print("Omni Setup")
    print("=" * 55)
    print("Press Right Shift + O, speak your question, and get answers on your screen.\n")

    api_key = input("Enter your Google Gemini API Key (or press Enter to skip): ").strip()
    if api_key:
        Config.save_api_key(api_key)
        print("Saved GEMINI_API_KEY successfully!\n")

def main():
    parser = argparse.ArgumentParser(description="Omni: Ambient Desktop AI Agent")
    parser.add_argument("--setup", action="store_true", help="Run interactive configuration setup")
    parser.add_argument("--test-screen", action="store_true", help="Test screen capture and exit")
    parser.add_argument("--ask", type=str, help="Take a screenshot and ask Gemini immediately with a text prompt")
    args = parser.parse_args()

    if args.test_screen:
        from omni.screen import ScreenCapture
        print("Testing screenshot capture...")
        p = ScreenCapture.capture()
        print(f"Screenshot captured: {p} ({p.stat().st_size} bytes)")
        return

    if args.setup:
        setup_wizard()
    elif not Config.GEMINI_API_KEY and sys.stdin.isatty():
        setup_wizard()

    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

    coordinator = AppCoordinator()

    if args.ask:
        coordinator.start()
        print(f"\n[Omni] Capturing screen and querying Gemini with prompt: '{args.ask}'...")
        import threading
        from omni.screen import ScreenCapture
        
        def run_one_shot():
            try:
                screen_path = ScreenCapture.capture()
                coordinator.hud.show(status="Analyzing screen...")
                coordinator.hud.set_content(f"### ⚡ Analyzing Screen\n**Prompt:** *{args.ask}*\n\nThinking...")
                
                if not coordinator.brain:
                    coordinator.hud.set_content("⚠️ GEMINI_API_KEY is not set in `.env`.")
                    return
                
                stream = coordinator.brain.ask_stream(
                    image_path=screen_path,
                    audio_path=None,
                    text_prompt=args.ask
                )
                coordinator.hud.set_content("")
                coordinator.hud.set_status("⚡ Streaming answer...")
                for chunk in stream:
                    coordinator.hud.append_token(chunk)
                coordinator.hud.set_status("💡 Answer Ready • Press Esc to close")
            except Exception as e:
                coordinator.hud.set_content(f"### ❌ Error\n```\n{e}\n```")
                coordinator.hud.set_status("❌ Error")

        threading.Thread(target=run_one_shot, daemon=True).start()
        AppHelper.runEventLoop()
        return

    coordinator.start()
    AppHelper.runEventLoop()

if __name__ == "__main__":
    main()
