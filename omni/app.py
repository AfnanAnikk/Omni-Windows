import threading
import sys
import os
import AppKit
from PyObjCTools import AppHelper

from omni.config import Config
from omni.audio import AudioRecorder
from omni.screen import ScreenCapture
from omni.ai import GeminiBrain
from omni.voice import SpeechEngine
from omni.ui.panel import OmniHUD
from omni.ui.indicator import MicIndicator
from omni.ui.status_bar import StatusBarApp
from omni.hotkey import HotkeyListener

class AppCoordinator:
    """Central orchestrator for Omni."""

    def __init__(self):
        Config.ensure_dirs()
        self.hud = OmniHUD()
        self.indicator = MicIndicator()
        self.status_bar = StatusBarApp(self)
        self.audio = AudioRecorder()
        self.voice = SpeechEngine(Config.VOICE_NAME)
        self.brain = None

        # Stop speech and hide indicator when user dismisses HUD
        self.hud.on_dismiss = self.handle_dismiss
        
        if Config.GEMINI_API_KEY:
            try:
                self.brain = GeminiBrain()
            except Exception as e:
                print(f"[Omni] Failed to initialize Gemini: {e}")

        self.hotkey_listener = HotkeyListener(
            on_trigger_start=self.handle_trigger_start,
            on_trigger_stop=self.handle_trigger_stop
        )

        self.screenshot_path = None
        self._is_processing = False
        self._is_cancelled = False

    def start(self):
        """Starts listeners."""
        self.hotkey_listener.start()
        print("Omni is active. Hold Cmd + 0 to speak, release to answer.")

    def toggle_trigger(self):
        """Manual trigger invoked via menu bar."""
        if not self.audio.is_recording and not self._is_processing:
            self.handle_trigger_start()
        elif self.audio.is_recording:
            self.handle_trigger_stop()

    def handle_dismiss(self):
        """Immediately halts speech and ensures indicator is hidden."""
        self._is_cancelled = True
        self.voice.stop()
        self.indicator.hide()

    def handle_trigger_start(self):
        """Trigger start (Hold Cmd + 0): silent screenshot + mic recording, NO window popup."""
        if self._is_processing:
            return

        # Interrupt any current speech and dismiss previous HUD
        self._is_cancelled = False
        self.voice.stop()
        self.hud.hide()

        print("[Omni] 🎙️ Recording started (Holding Cmd + 0)...")
        self.status_bar.set_status_text("Omni [•]")

        # 1. Show Siri-style listening pill in the top-right corner
        self.indicator.start_listening()

        # 2. Capture screen silently in background thread while user speaks
        self.screenshot_path = None
        threading.Thread(target=self._capture_screen_async, daemon=True).start()

        # 3. Start audio recording
        self.audio.start()

    def _capture_screen_async(self):
        try:
            self.screenshot_path = ScreenCapture.capture()
        except Exception as e:
            print(f"[Omni] Screen capture error: {e}")
            self.screenshot_path = None

    def handle_trigger_stop(self):
        """Trigger stop (Released Cmd + 0): animate thinking, inference worker shows HUD only when ready."""
        if not self.audio.is_recording:
            return

        print("[Omni] ⚡ Recording finished (Released Cmd + 0). Analyzing...")
        self.status_bar.set_status_text("Omni")
        self._is_processing = True

        # Stop audio recording and analyze if user spoke
        audio_path = self.audio.stop()

        # If user didn't say anything (accidental tap or silence)
        if not audio_path:
            print("[Omni] 🤫 Silence or accidental tap detected. Dismissing indicator cleanly.")
            self.indicator.hide()
            self._is_processing = False
            return

        # 1. Transition top-right indicator to animated Thinking state
        self.indicator.start_processing()

        # 2. Run inference in background worker
        worker = threading.Thread(
            target=self._run_inference,
            args=(self.screenshot_path, audio_path),
            daemon=True
        )
        worker.start()

    def _run_inference(self, screenshot_path, audio_path):
        """Inference worker: keeps indicator alive until first token arrives, then shows solution HUD."""
        try:
            if not self.brain:
                if Config.GEMINI_API_KEY:
                    self.brain = GeminiBrain()
                else:
                    self.indicator.hide()
                    self.hud.set_content("GEMINI_API_KEY is not set.")
                    self.hud.show(status="Error")
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
                    # First token arrived! Hide top-right indicator and show the solution HUD
                    self.indicator.hide()
                    self.hud.set_content("")
                    self.hud.show(status="Omni")

                self.hud.append_token(chunk)
                full_response += chunk
                token_count += 1

            if token_count == 0:
                self.indicator.hide()
                print("[Omni] 🤫 No response generated (silence/aborted). Keeping HUD hidden.")
            else:
                # Speak only if user has not explicitly dismissed/cancelled
                if not self._is_cancelled:
                    print("[Omni] 🔊 Speaking response takeaway...")
                    self.voice.speak(full_response)
                else:
                    print("[Omni] Speech skipped (cancelled by user).")

            self.hud.set_status("Ready")

        except Exception as e:
            print(f"[Omni] Inference error: {e}")
            self.indicator.hide()
            self.hud.set_content(f"Error:\n\n{e}")
            self.hud.show(status="Error")
        finally:
            self._is_processing = False
            self.status_bar.set_status_text("Omni")
