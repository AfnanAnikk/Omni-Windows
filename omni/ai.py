import os
from pathlib import Path
from typing import Generator, Optional
from google import genai
from google.genai import types
from omni.config import Config

SYSTEM_INSTRUCTION = """You are Omni, a fast, direct AI assistant for macOS.
The user pressed a hotkey on their Mac and spoke a query while looking at their screen.
You receive:
1. The exact screenshot of what the user is currently looking at.
2. The user's spoken voice audio.

Your mission:
Provide a crystal-clear, direct, accurate answer tailored to the user's spoken question and the visual context.

Formatting & Response Guidelines:
1. Punchy Direct Answer First: State the single-sentence final answer, key result, or direct fix immediately on the very first line (max 15-20 words). This sentence will be spoken aloud to the user while the full detailed explanation and code blocks appear on screen.
2. For Math & Logic Problems:
   - State the final result clearly first (e.g. "**Result:** x = 3, y = -1").
   - Follow with a structured, step-by-step derivation/explanation.
   - Use standard LaTeX math formatting for equations ($...$ for inline, $$...$$ for display equations) and clear notation (fractions, roots, exponents).
3. For Programming & Debugging:
   - Pinpoint the exact line or error shown on screen.
   - Provide the corrected code in properly syntax-highlighted code blocks (e.g. ```python, ```swift).
4. For General Screen Questions (e.g. summarizing an article, explaining a chart, reading a doc):
   - Be concise, high-signal, and well-structured with bullet points.
5. Tone:
   - No conversational fluff (skip "Sure, I can help with that!", "Looking at your screen..."). Jump straight into the solution.
"""

ROUTER_SYSTEM_INSTRUCTION = """You are an intelligent intent router and assistant for Omni on macOS.
The user held a push-to-talk hotkey and spoke a query.

Analyze the user's spoken audio:
1. If the audio is silent, inaudible, contains only ambient room noise or breathing, or the user did NOT ask any question or speak any meaningful words:
   Output EXACTLY and ONLY: [NO_SPEECH]

2. If the user's question explicitly or implicitly asks about, refers to, or requires seeing their computer screen (e.g. asking about code on screen, an error message, an open webpage, an image, a document, UI elements, or saying "what is this", "explain this", "look at my screen", "why is this failing", "summarize this page"):
   Output EXACTLY and ONLY: [REQUIRES_SCREEN]

3. Otherwise, if the user's question is a general conversational question, greeting, general coding question, math problem, or general knowledge question that does NOT require visual screen context (e.g. "how are you", "what is the capital of France", "write a quicksort in python", "what is 42 * 7", "tell me a joke"):
   Directly answer the user's question immediately, clearly, and concisely. Keep the very first sentence punchy and direct.
"""

class GeminiBrain:
    """Multimodal reasoning engine powered by Google Gemini 3.5 / 3.8 Flash."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError(
                "Gemini API Key is not configured. Please set GEMINI_API_KEY in .env or pass it to GeminiBrain."
            )
        self.client = genai.Client(api_key=self.api_key)
        self.active_model = self._detect_best_model()

    def _detect_best_model(self) -> str:
        """Dynamically identifies the best available Gemini model for the API key."""
        preferred = Config.GEMINI_MODEL
        if preferred and "2.0" not in preferred and "1.5" not in preferred and "2.5" not in preferred:
            return preferred

        return "gemini-3-flash-preview"

    def ask_stream(
        self,
        image_path: Optional[Path],
        audio_path: Optional[Path] = None,
        text_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Intelligently streams responses. Uses AI to avoid sending screenshots for general queries.
        """
        has_audio = audio_path and audio_path.exists() and audio_path.stat().st_size > 1000
        has_image = image_path and image_path.exists()

        # Step 1: AI Screen Intent Router (for audio voice queries)
        # If the user spoke, ask AI if the query actually needs the screen!
        if has_audio and has_image:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
            router_config = types.GenerateContentConfig(
                system_instruction=ROUTER_SYSTEM_INSTRUCTION,
                temperature=0.2,
            )

            try:
                # Fast classification via sub-200ms lightweight model
                router_stream = self.client.models.generate_content_stream(
                    model="gemini-3.1-flash-lite",
                    contents=[
                        audio_part,
                        "Listen to my voice and determine if this needs my screen or answer directly."
                    ],
                    config=router_config,
                )

                first_chunk = ""
                requires_screen = False

                for chunk in router_stream:
                    if chunk.text:
                        if not first_chunk:
                            first_chunk = chunk.text
                            if "[NO_SPEECH]" in first_chunk:
                                print("[GeminiBrain] 🤫 Router detected silence/no speech. Aborting query.")
                                return
                            elif "[REQUIRES_SCREEN]" in first_chunk:
                                requires_screen = True
                                break
                            else:
                                yield chunk.text
                        else:
                            yield chunk.text

                # If the AI directly answered the query without needing the screen, we're done!
                if not requires_screen and first_chunk:
                    return

            except Exception as e:
                print(f"[GeminiBrain] Router check error: {e}. Falling back to full multimodal query...")

        # Step 2: Full Multimodal Query (Screen + Audio or Text)
        contents = []

        # Attach optimized screenshot
        if has_image:
            with open(image_path, "rb") as f:
                img_bytes = f.read()
            mime = "image/jpeg" if str(image_path).endswith(('.jpg', '.jpeg')) else "image/png"
            contents.append(
                types.Part.from_bytes(data=img_bytes, mime_type=mime)
            )

        # Attach spoken audio if available
        if has_audio:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            contents.append(
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
            )
            contents.append("Listen to my spoken voice audio and answer my question based on what's visible on my screen.")
        elif text_prompt:
            contents.append(text_prompt)
        else:
            contents.append("Analyze the most important content on my screen and provide a helpful, concise summary or solution.")

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
        )

        candidates = [self.active_model, "gemini-3-flash-preview", "gemini-3.8-flash", "gemini-3.1-flash-lite"]
        unique_models = []
        for c in candidates:
            if c not in unique_models:
                unique_models.append(c)

        last_error = None
        for m in unique_models:
            try:
                response_stream = self.client.models.generate_content_stream(
                    model=m,
                    contents=contents,
                    config=config,
                )
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                print(f"[GeminiBrain] Model {m} encountered error: {e}. Trying next...")
                last_error = e
                continue

        if last_error:
            raise last_error
