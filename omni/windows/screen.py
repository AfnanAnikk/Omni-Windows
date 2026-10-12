import os
from pathlib import Path
from omni.config import Config

class WindowsScreenCapture:
    """Fast, silent screen capture for Windows using mss or Pillow."""

    @staticmethod
    def capture() -> Path:
        Config.ensure_dirs()
        target_path = Config.SCREENSHOT_FILE
        raw_path = Config.TMP_DIR / "raw_capture.png"

        try:
            # Try mss first (takes ~10ms, highest speed)
            import mss
            import mss.tools
            from PIL import Image

            with mss.mss() as sct:
                # Primary monitor (index 1 is primary display, index 0 is bounding box of all displays)
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(raw_path))

            # Resize to max 1280px width for fast Gemini inference
            with Image.open(raw_path) as img:
                img = img.convert("RGB")
                if img.width > 1280:
                    ratio = 1280 / float(img.width)
                    new_height = int(img.height * ratio)
                    img = img.resize((1280, new_height), Image.Resampling.LANCZOS)
                img.save(target_path, "JPEG", quality=65, optimize=True)

            raw_path.unlink(missing_ok=True)
            return target_path

        except Exception as e:
            # Fallback to Pillow ImageGrab
            try:
                from PIL import ImageGrab, Image
                img = ImageGrab.grab()
                img = img.convert("RGB")
                if img.width > 1280:
                    ratio = 1280 / float(img.width)
                    new_height = int(img.height * ratio)
                    img = img.resize((1280, new_height), Image.Resampling.LANCZOS)
                img.save(target_path, "JPEG", quality=65, optimize=True)
                return target_path
            except Exception as e_inner:
                raise RuntimeError(f"Windows screen capture failed: {e_inner}")
