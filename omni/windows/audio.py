import os
import time
import wave
import struct
import math
from pathlib import Path
from typing import Optional
from omni.config import Config

class WindowsAudioRecorder:
    """Windows audio recording using sounddevice with energy analysis."""

    def __init__(self):
        self.sample_rate = 16000
        self.channels = 1
        self._frames = []
        self._stream = None
        self._is_recording = False
        self._start_time = 0.0

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def play_sound(self, sound_type: str = "start"):
        """Plays subtle Windows system sound cue."""
        if not Config.PLAY_SOUNDS:
            return
        try:
            import winsound
            if sound_type == "start":
                winsound.MessageBeep(winsound.MB_OK)
            else:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def start(self):
        """Starts recording audio from default microphone."""
        if self._is_recording:
            return

        Config.ensure_dirs()
        self._frames = []
        self._is_recording = True
        self._start_time = time.time()
        self.play_sound("start")

        try:
            import sounddevice as sd

            def audio_callback(indata, frames, time_info, status):
                if self._is_recording:
                    self._frames.append(indata.copy())

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="int16",
                    callback=audio_callback
                )
                self._stream.start()
            except Exception:
                # Fallback to device's native samplerate if 16kHz is unsupported by the driver
                dev_info = sd.query_devices(kind='input')
                self.sample_rate = int(dev_info.get('default_samplerate', 44100))
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="int16",
                    callback=audio_callback
                )
                self._stream.start()
        except Exception as e:
            print(f"[WindowsAudioRecorder] Failed to start sounddevice stream: {e}")
            self._is_recording = False

    def has_speech(self, target_path: Path, min_duration: float = 0.45, min_peak: int = 450, min_rms: float = 40.0) -> bool:
        """Analyzes audio waveform to determine if the user actually spoke vs silence/tap."""
        duration = time.time() - self._start_time
        if duration < min_duration:
            print(f"[WindowsAudioRecorder] Press was too brief ({duration:.2f}s < {min_duration}s). Ignored.")
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

                print(f"[WindowsAudioRecorder] Audio analysis -> Duration: {duration:.2f}s, Peak: {peak}, RMS: {rms:.1f}")

                if peak < min_peak and rms < min_rms:
                    print("[WindowsAudioRecorder] Silence detected. No speech detected in recording.")
                    return False

                return True
        except Exception as e:
            print(f"[WindowsAudioRecorder] Voice detection check error: {e}")
            return True

    def stop(self) -> Optional[Path]:
        """Stops recording and returns the path to the recorded WAV file only if speech was detected."""
        if not self._is_recording:
            return None

        self._is_recording = False
        self.play_sound("stop")

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if not self._frames:
            return None

        target_path = Config.AUDIO_FILE
        try:
            import numpy as np
            audio_data = np.concatenate(self._frames, axis=0)

            with wave.open(str(target_path), "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2) # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())

            if target_path.exists() and target_path.stat().st_size > 1000:
                if self.has_speech(target_path):
                    return target_path
        except Exception as e:
            print(f"[WindowsAudioRecorder] Error saving audio file: {e}")

        return None
