import threading
import sys
import os
import webview
from omni.config import Config
from omni.ai import GeminiBrain
from omni.windows.screen import WindowsScreenCapture
from omni.windows.audio import WindowsAudioRecorder
from omni.windows.voice import WindowsSpeechEngine
from omni.windows.hotkey import WindowsHotkeyListener
from omni.windows.ui import WindowsHUD, WindowsIndicator, HUD_HTML, INDICATOR_HTML
from omni.windows.tray import WindowsTrayApp

class WindowsApiBridge:
    """JS bridge exposed to pywebview HUD window."""
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def dismiss(self):
        self.coordinator.handle_dismiss()

class WindowsAppCoordinator:
    """Central orchestrator for Omni on Windows."""

    def __init__(self):
        Config.ensure_dirs()
        self.hud = WindowsHUD(self)
        self.indicator = WindowsIndicator()
        self.tray = WindowsTrayApp(self)
        self.audio = WindowsAudioRecorder()
        self.voice = WindowsSpeechEngine(Config.VOICE_NAME)
        self.brain = None

        if Config.GEMINI_API_KEY:
            try:
                self.brain = GeminiBrain()
            except Exception as e:
                print(f"[WindowsOmni] Gemini init error: {e}")

        self.hotkey = WindowsHotkeyListener(
            on_trigger_start=self.handle_trigger_start,
            on_trigger_stop=self.handle_trigger_stop
        )

        self.screenshot_path = None
        self._is_processing = False
        self._is_cancelled = False
        self.api_bridge = WindowsApiBridge(self)

    def start(self):
        """Starts listeners and tray."""
        self.tray.start()
        self.hotkey.start()
        print("[WindowsOmni] Omni is active. Hold Ctrl + 0 to speak, release to answer.")

    def toggle_trigger(self):
        if not self.audio.is_recording and not self._is_processing:
            self.handle_trigger_start()
        elif self.audio.is_recording:
            self.handle_trigger_stop()

    def handle_dismiss(self):
        self._is_cancelled = True
        self.voice.stop()
        self.indicator.hide()
        self.hud.hide()

    def handle_trigger_start(self):
        if self._is_processing:
            return

        self._is_cancelled = False
        self.voice.stop()
        self.hud.hide()

        print("[WindowsOmni] 🎙️ Recording started (Holding Ctrl + 0)...")
        self.indicator.start_listening()

        self.screenshot_path = None
        threading.Thread(target=self._capture_screen_async, daemon=True).start()
        self.audio.start()

    def _capture_screen_async(self):
        try:
            self.screenshot_path = WindowsScreenCapture.capture()
        except Exception as e:
            print(f"[WindowsOmni] Screen capture error: {e}")
            self.screenshot_path = None

    def handle_trigger_stop(self):
        if not self.audio.is_recording:
            return

        print("[WindowsOmni] ⚡ Recording finished (Released Ctrl + 0). Analyzing...")
        self._is_processing = True

        audio_path = self.audio.stop()

        # Reject accidental tap or room silence
        if not audio_path:
            print("[WindowsOmni] 🤫 Silence or accidental tap detected. Dismissing indicator.")
            self.indicator.hide()
            self._is_processing = False
            return

        # Animate thinking indicator
        self.indicator.start_processing()

        worker = threading.Thread(
            target=self._run_inference,
            args=(self.screenshot_path, audio_path),
            daemon=True
        )
        worker.start()

    def _run_inference(self, screenshot_path, audio_path):
        try:
            if not self.brain:
                if Config.GEMINI_API_KEY:
                    self.brain = GeminiBrain()
                else:
                    self.indicator.hide()
                    self.hud.set_content("⚠️ GEMINI_API_KEY is not set in `.env`.")
                    self.hud.show()
                    self._is_processing = False
                    return

            stream = self.brain.ask_stream(
                image_path=screenshot_path,
                audio_path=audio_path
            )

            full_response = ""
            token_count = 0
            for chunk in stream:
                if token_count == 0:
                    # First token arrived: hide indicator and show HUD
                    self.indicator.hide()
                    self.hud.set_content("")
                    self.hud.show()

                self.hud.append_token(chunk)
                full_response += chunk
                token_count += 1

            if token_count == 0:
                self.indicator.hide()
                print("[WindowsOmni] 🤫 No response generated (silence/aborted). Keeping HUD hidden.")
            else:
                if not self._is_cancelled:
                    print("[WindowsOmni] 🔊 Speaking takeaway...")
                    self.voice.speak(full_response)
                else:
                    print("[WindowsOmni] Speech skipped (cancelled).")

            self.hud.set_status("Ready")

        except Exception as e:
            print(f"[WindowsOmni] Inference error: {e}")
            self.indicator.hide()
            self.hud.set_content(f"### ❌ Error\n```\n{e}\n```")
            self.hud.show()
        finally:
            self._is_processing = False

    def quit(self):
        self.handle_dismiss()
        self.hotkey.stop()
        self.tray.stop()
        os._exit(0)
