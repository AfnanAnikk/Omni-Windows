import subprocess
import shutil
import os
import time
import wave
import struct
import math
from pathlib import Path
from typing import Optional
from omni.config import Config

class AudioRecorder:
    """Manages audio recording using ffmpeg and afplay with voice energy detection."""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.ffmpeg_bin = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        self._start_time: float = 0

    @property
    def is_recording(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def play_sound(self, sound_name: str = "Tink"):
        """Plays subtle macOS system sound in the background."""
        if not Config.PLAY_SOUNDS:
            return
        sound_path = Path(f"/System/Library/Sounds/{sound_name}.aiff")
        if sound_path.exists():
            subprocess.Popen(
                ["afplay", str(sound_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    def start(self):
        """Starts recording audio from default microphone."""
        if self.is_recording:
            return

        Config.ensure_dirs()
        target_path = Config.AUDIO_FILE
        if target_path.exists():
            try:
                target_path.unlink()
            except OSError:
                pass

        self.play_sound("Tink")

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f", "avfoundation",
            "-i", Config.AUDIO_DEVICE,
            "-ar", "16000",          # 16kHz is optimal for speech
            "-ac", "1",              # mono
            "-c:a", "pcm_s16le",     # 16-bit PCM WAV
            str(target_path)
        ]

        self._start_time = time.time()
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def has_speech(self, target_path: Path, min_duration: float = 0.45, min_peak: int = 450, min_rms: float = 40.0) -> bool:
        """Analyzes audio waveform to determine if the user actually spoke vs silence/tap."""
        duration = time.time() - self._start_time
        if duration < min_duration:
            print(f"[AudioRecorder] Press was too brief ({duration:.2f}s < {min_duration}s). Ignored.")
            return False

        if not target_path or not target_path.exists() or target_path.stat().st_size < 1000:
            return False

        try:
            with wave.open(str(target_path), "rb") as wf:
                n_frames = wf.getnframes()
                if n_frames == 0:
                    return False
                raw_data = wf.readframes(n_frames)
                samples = struct.unpack(f"<{len(raw_data) // 2}h", raw_data)
                if not samples:
                    return False

                peak = max(abs(s) for s in samples)
                rms = math.sqrt(sum(s * s for s in samples) / len(samples))

                print(f"[AudioRecorder] Audio analysis -> Duration: {duration:.2f}s, Peak: {peak}, RMS: {rms:.1f}")

                # If audio is essentially silent (below speech threshold)
                if peak < min_peak and rms < min_rms:
                    print("[AudioRecorder] Silence detected. No speech detected in recording.")
                    return False

                return True
        except Exception as e:
            print(f"[AudioRecorder] Voice detection check error: {e}")
            return True

    def stop(self) -> Optional[Path]:
        """Stops recording and returns the path to the recorded WAV file only if speech was detected."""
        if not self.process:
            return None

        self.play_sound("Pop")

        proc = self.process
        self.process = None

        if proc.poll() is None:
            try:
                proc.communicate(input=b"q", timeout=2)
            except Exception:
                try:
                    proc.terminate()
                    proc.wait(timeout=1)
                except Exception:
                    proc.kill()

        target_path = Config.AUDIO_FILE
        if target_path.exists() and target_path.stat().st_size > 1000:
            if self.has_speech(target_path):
                return target_path

        return None
