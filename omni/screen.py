import subprocess
import os
from pathlib import Path
from omni.config import Config

class ScreenCapture:
    """Manages silent, fast, and optimized macOS screen captures."""

    @staticmethod
    def capture() -> Path:
        Config.ensure_dirs()
        target_path = Config.SCREENSHOT_FILE
        raw_path = Config.TMP_DIR / "raw_capture.jpg"

        try:
            # 1. Fast silent JPEG capture
            subprocess.run(
                ["/usr/sbin/screencapture", "-x", "-t", "jpg", str(raw_path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # 2. Fast downsample to 1280px width with quality 65 using native macOS sips tool
            # Reduces payload from ~5.4MB to ~200KB for near-instant upload to Gemini
            subprocess.run(
                ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "65", "-Z", "1280", str(raw_path), "--out", str(target_path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            raw_path.unlink(missing_ok=True)

            if target_path.exists() and target_path.stat().st_size > 0:
                return target_path
            raise RuntimeError("Screenshot file was not created or is empty.")
        except Exception as e:
            # Fallback to direct capture if sips fails
            try:
                subprocess.run(
                    ["/usr/sbin/screencapture", "-x", "-t", "jpg", str(target_path)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return target_path
            except Exception:
                raise RuntimeError(f"Failed to capture screen: {e}")
