import re
import os
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Optional
from omni.config import Config

class WindowsSpeechEngine:
    """High-fidelity Speech Engine for Windows.
    
    Supports:
    1. Microsoft Neural TTS (Edge TTS) - Natural, expressive voices (Ava, Andrew, Jenny).
    2. Fallback to Windows native SAPI5 Speech Synthesizer if offline.
    3. Instant cancellation / interruption when Esc is pressed.
    """

    def __init__(self, voice_preference: Optional[str] = None):
        self.voice_name = voice_preference or getattr(Config, "VOICE_NAME", "en-US-AvaNeural")
        self._speech_gen = 0
        self._player_proc: Optional[subprocess.Popen] = None
        self._sapi_voice = None

        self.cache_dir = Config.TMP_DIR / "voice"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._init_sapi_fallback()

    def _init_sapi_fallback(self):
        try:
            import win32com.client
            self._sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
        except Exception:
            self._sapi_voice = None

    @property
    def is_speaking(self) -> bool:
        if self._player_proc and self._player_proc.poll() is None:
            return True
        return False

    def clean_math(self, text: str) -> str:
        """Converts LaTeX math formulas to natural spoken English."""
        text = re.sub(r'\\\\\((.*?)\\\\\)', r' \1 ', text)
        text = re.sub(r'\\\[(.*?)\\\]', r' \1 ', text)
        text = re.sub(r'\$\$(.*?)\$\$', r' \1 ', text)
        text = re.sub(r'\$(.*?)\$', r' \1 ', text)
        text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1 over \2', text)
        text = re.sub(r'\\sqrt\{([^}]+)\}', r'square root of \1', text)
        text = re.sub(r'\^2', ' squared', text)
        text = re.sub(r'\^3', ' cubed', text)
        text = re.sub(r'\^\{([^}]+)\}', r' to the power of \1', text)
        text = re.sub(r'\\\w+', '', text)
        return text

    def extract_spoken_summary(self, markdown_text: str, max_sentences: int = 2, max_chars: int = 180) -> str:
        """Extracts a punchy 1-2 sentence spoken summary from markdown output."""
        has_code = "```" in markdown_text

        # 1. Strip code blocks completely
        text_without_code = re.sub(r'```[\s\S]*?```', '', markdown_text)

        # 2. Convert LaTeX math
        clean = self.clean_math(text_without_code)

        # 3. Clean markdown formatting
        clean = re.sub(r'[*_~`]', '', clean)
        clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean)

        # 4. Find the first informative paragraph
        raw_paragraphs = clean.split("\n\n")
        valid_blocks = []
        for p in raw_paragraphs:
            p = p.strip()
            lines = [l.strip() for l in p.splitlines() if l.strip() and not l.strip().startswith(('#', '|', '---', '==='))]
            if lines:
                block = " ".join(lines)
                if not re.match(r'^(\d+\.|\-|\+)\s+', block):
                    valid_blocks.append(block)

        if not valid_blocks:
            return "I've placed the solution on your screen." if has_code else ""

        text = valid_blocks[0]
        text = re.sub(r'^[>\s*+-]+', '', text)
        text = re.sub(r'^(Result|Answer|Summary|Overview|Solution|Fix):\s*', '', text, flags=re.IGNORECASE)

        # Extract strictly first 1-2 sentences
        sentence_matches = re.split(r'(?<=[.!?])\s+', text)
        spoken_sentences = []
        total_len = 0

        for s in sentence_matches:
            s = s.strip()
            if not s or s in ('.', '!', '?'):
                continue
            if spoken_sentences and (len(spoken_sentences) >= max_sentences or total_len + len(s) > max_chars):
                break
            spoken_sentences.append(s)
            total_len += len(s)

        summary = " ".join(spoken_sentences).strip()

        if has_code and "placed the code" not in summary.lower() and "on your screen" not in summary.lower():
            if summary and not summary.endswith(('.', '!', '?')):
                summary += '.'
            summary += " I've placed the code on your screen."

        summary = re.sub(r'\s+', ' ', summary).strip()
        return summary

    def speak(self, text: str):
        """Speaks the concise takeaway asynchronously."""
        if not getattr(Config, "VOICE_ENABLED", True):
            return

        speech_text = self.extract_spoken_summary(text)
        if not speech_text:
            return

        print(f"[WindowsSpeechEngine] 🗣️ Speaking: '{speech_text}'")

        self.stop()
        self._speech_gen += 1
        current_gen = self._speech_gen

        threading.Thread(
            target=self._speech_worker,
            args=(speech_text, current_gen),
            daemon=True
        ).start()

    def _speech_worker(self, speech_text: str, current_gen: int):
        if current_gen != self._speech_gen:
            return

        out_file = self.cache_dir / f"speech_{current_gen}.mp3"
        try:
            # 1. Generate speech via Edge TTS
            import edge_tts
            communicate = edge_tts.Communicate(speech_text, self.voice_name)
            asyncio.run(communicate.save(str(out_file)))

            if current_gen != self._speech_gen or not out_file.exists():
                return

            # 2. Play via PowerShell MediaPlayer (native Windows, supports MP3 out of the box)
            ps_script = f"""
            Add-Type -AssemblyName presentationCore
            $player = New-Object System.Windows.Media.MediaPlayer
            $player.Open('{str(out_file).replace("'", "''")}')
            $player.Play()
            Start-Sleep -Milliseconds 300
            while ($player.NaturalDuration.HasTimeSpan -and $player.Position -lt $player.NaturalDuration.TimeSpan) {{
                Start-Sleep -Milliseconds 100
            }}
            """
            # CREATE_NO_WINDOW = 0x08000000 ensures no console flash on Windows
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            self._player_proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags
            )
            self._player_proc.wait()

        except Exception as e:
            print(f"[WindowsSpeechEngine] Edge TTS playback failed, falling back to SAPI: {e}")
            self._fallback_sapi(speech_text, current_gen)
        finally:
            try:
                out_file.unlink(missing_ok=True)
            except Exception:
                pass

    def _fallback_sapi(self, text: str, current_gen: int):
        if current_gen != self._speech_gen:
            return
        if self._sapi_voice:
            try:
                # SVSFlagsAsync = 1
                self._sapi_voice.Speak(text, 1)
            except Exception:
                pass

    def stop(self):
        """Immediately halts any in-progress speech playback."""
        self._speech_gen += 1
        if self._player_proc and self._player_proc.poll() is None:
            try:
                self._player_proc.terminate()
            except Exception:
                pass
            self._player_proc = None
        if self._sapi_voice:
            try:
                # SVSFPurgeBeforeSpeak = 2
                self._sapi_voice.Speak("", 2)
            except Exception:
                pass
