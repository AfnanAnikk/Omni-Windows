import re
import os
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Optional

import AppKit
from PyObjCTools import AppHelper
from omni.config import Config

class SpeechEngine:
    """High-fidelity Speech Engine for Omni.
    
    Supports:
    1. Microsoft Neural TTS (Edge TTS) - Natural, expressive, human voices (Ava, Andrew, Jenny, Brian).
    2. Fallback to native macOS NSSpeechSynthesizer if offline or configured.
    3. Instant cancellation / interruption via process killing and generation IDs.
    """

    def __init__(self, voice_preference: Optional[str] = None):
        self.voice_name = voice_preference or getattr(Config, "VOICE_NAME", "en-US-AvaNeural")
        self.engine_type = getattr(Config, "VOICE_ENGINE", "edge").lower()
        self._speech_gen = 0
        self._player_proc: Optional[subprocess.Popen] = None
        self._synth = None

        # Temp directory for speech audio cache
        self.cache_dir = Path("/tmp/omni/voice")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize macOS fallback synthesizer lazily
        self._init_fallback_synth()

    def _init_fallback_synth(self):
        try:
            self._synth = AppKit.NSSpeechSynthesizer.alloc().init()
            voices = [str(v) for v in AppKit.NSSpeechSynthesizer.availableVoices()]
            for v in voices:
                if "samantha" in v.lower():
                    self._synth.setVoice_(v)
                    break
        except Exception:
            self._synth = None

    @property
    def is_speaking(self) -> bool:
        if self._player_proc and self._player_proc.poll() is None:
            return True
        if self._synth and self._synth.isSpeaking():
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
        """Extracts a punchy 1-2 sentence spoken summary (under ~10 seconds) from markdown output."""
        has_code = "```" in markdown_text

        # 1. Strip code blocks completely
        text_without_code = re.sub(r'```[\s\S]*?```', '', markdown_text)

        # 2. Convert LaTeX math
        clean = self.clean_math(text_without_code)

        # 3. Clean markdown formatting (* _ ~ ` [link](url))
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

        # 5. Clean leading bullet markers or quotes
        text = re.sub(r'^[>\s*+-]+', '', text)

        # 6. Remove robotic label prefixes ("Result:", "Answer:", "Summary:", etc.)
        text = re.sub(r'^(Result|Answer|Summary|Overview|Solution|Fix):\s*', '', text, flags=re.IGNORECASE)

        # 7. Extract strictly first 1-2 sentences
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

        # Append screen reference note if code was generated
        if has_code and "placed the code" not in summary.lower() and "on your screen" not in summary.lower():
            if summary and not summary.endswith(('.', '!', '?')):
                summary += '.'
            summary += " I've placed the code on your screen."

        summary = re.sub(r'\s+', ' ', summary).strip()
        return summary

    def speak(self, text: str):
        """Speaks the concise takeaway asynchronously."""
        if not getattr(Config, "VOICE_ENABLED", True):
            print("[SpeechEngine] VOICE_ENABLED is False, skipping speech.")
            return

        speech_text = self.extract_spoken_summary(text)
        if not speech_text:
            print("[SpeechEngine] Spoken summary was empty, skipping speech.")
            return

        print(f"[SpeechEngine] 🗣️ Speaking: '{speech_text}'")

        # Advance generation to cancel any previously queued/running speech
        self.stop()
        self._speech_gen += 1
        current_gen = self._speech_gen

        # Launch background audio worker
        threading.Thread(
            target=self._speech_worker,
            args=(speech_text, current_gen),
            daemon=True
        ).start()

    def _speech_worker(self, speech_text: str, current_gen: int):
        """Generates audio and streams it to macOS audio output."""
        if current_gen != self._speech_gen:
            return

        # Attempt Neural Edge TTS first if configured
        if self.engine_type == "edge":
            try:
                import edge_tts
                target_file = self.cache_dir / f"speech_{current_gen}.mp3"

                async def _generate():
                    comm = edge_tts.Communicate(speech_text, self.voice_name)
                    await comm.save(str(target_file))

                asyncio.run(_generate())

                # Check if generation wasn't invalidated while downloading
                if current_gen != self._speech_gen:
                    if target_file.exists():
                        target_file.unlink(missing_ok=True)
                    return

                # Play via afplay
                if target_file.exists():
                    self._player_proc = subprocess.Popen(
                        ["afplay", str(target_file)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    self._player_proc.wait()
                    target_file.unlink(missing_ok=True)
                    return
            except Exception as e:
                print(f"[SpeechEngine] Neural TTS failed ({e}), falling back to native macOS voice...")

        # Fallback to native macOS NSSpeechSynthesizer
        if current_gen == self._speech_gen and self._synth:
            def _speak_native():
                if current_gen == self._speech_gen:
                    self._synth.startSpeakingString_(speech_text)
            AppHelper.callAfter(_speak_native)

    def stop(self):
        """Instantly halts any active speech or player."""
        self._speech_gen += 1  # Invalidate pending tasks

        # 1. Kill any active afplay process immediately
        if self._player_proc:
            try:
                if self._player_proc.poll() is None:
                    self._player_proc.terminate()
            except Exception:
                pass
            self._player_proc = None

        # 2. Stop native macOS synthesizer
        if self._synth:
            try:
                if self._synth.isSpeaking():
                    self._synth.stopSpeaking()
            except Exception:
                pass
