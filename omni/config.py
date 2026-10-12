import os
import sys
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    APP_SUPPORT_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Omni"
else:
    APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "Omni"
APP_SUPPORT_ENV = APP_SUPPORT_DIR / ".env"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_ENV = PROJECT_ROOT / ".env"

# Prioritize App Support .env, then local project .env
try:
    if APP_SUPPORT_ENV.exists():
        load_dotenv(APP_SUPPORT_ENV)
    elif LOCAL_ENV.exists():
        load_dotenv(LOCAL_ENV)
    else:
        load_dotenv()
except Exception:
    try:
        if LOCAL_ENV.exists():
            load_dotenv(LOCAL_ENV)
        else:
            load_dotenv()
    except Exception:
        pass

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "ui_config.json"
DEFAULT_CSS_PATH = Path(__file__).resolve().parent / "ui" / "style.css"

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").strip()
    DEFAULT_HOTKEY = "ctrl+0" if sys.platform == "win32" else "cmd+0"
    HOTKEY = os.getenv("HOTKEY", DEFAULT_HOTKEY).strip().lower()
    TRIGGER_MODE = os.getenv("TRIGGER_MODE", "toggle").strip().lower()
    PLAY_SOUNDS = os.getenv("PLAY_SOUNDS", "true").strip().lower() in ("true", "1", "yes")
    VOICE_ENABLED = os.getenv("VOICE_ENABLED", "true").strip().lower() in ("true", "1", "yes")
    VOICE_ENGINE = os.getenv("VOICE_ENGINE", "edge").strip().lower()
    VOICE_NAME = os.getenv("VOICE_NAME", "en-US-AvaNeural").strip()
    DEFAULT_AUDIO_DEVICE = "default" if sys.platform == "win32" else ":0"
    AUDIO_DEVICE = os.getenv("AUDIO_DEVICE", DEFAULT_AUDIO_DEVICE).strip()
    MAX_RECORD_SECONDS = int(os.getenv("MAX_RECORD_SECONDS", "30"))

    # File paths for capture
    TMP_DIR = Path(tempfile.gettempdir()) / "omni"
    SCREENSHOT_FILE = TMP_DIR / "screen.jpg"
    AUDIO_FILE = TMP_DIR / "audio.wav"

    # UI Configuration paths
    UI_CONFIG_FILE = APP_SUPPORT_DIR / "ui_config.json"
    UI_CSS_FILE = APP_SUPPORT_DIR / "style.css"

    @classmethod
    def ensure_dirs(cls):
        try:
            cls.TMP_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
            # Seed user-editable files into Application Support if not present
            if not cls.UI_CONFIG_FILE.exists() and DEFAULT_CONFIG_PATH.exists():
                cls.UI_CONFIG_FILE.write_text(DEFAULT_CONFIG_PATH.read_text())
            if not cls.UI_CSS_FILE.exists() and DEFAULT_CSS_PATH.exists():
                cls.UI_CSS_FILE.write_text(DEFAULT_CSS_PATH.read_text())
        except Exception:
            pass

    @classmethod
    def load_ui_config(cls) -> dict:
        """Loads user UI configuration with fallback."""
        target = cls.UI_CONFIG_FILE if cls.UI_CONFIG_FILE.exists() else DEFAULT_CONFIG_PATH
        if target.exists():
            try:
                with open(target, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "window": {"width": 680, "height": 450, "border_radius": 14, "opacity": 0.96},
            "typography": {"font_size": 14.5, "line_height": 1.55}
        }

    @classmethod
    def load_css(cls) -> str:
        """Loads custom CSS stylesheet."""
        target = cls.UI_CSS_FILE if cls.UI_CSS_FILE.exists() else DEFAULT_CSS_PATH
        if target.exists():
            try:
                return target.read_text()
            except Exception:
                pass
        return ""

    @classmethod
    def save_api_key(cls, api_key: str):
        """Saves API key to user's Application Support directory."""
        cls.ensure_dirs()
        env_target = APP_SUPPORT_ENV if APP_SUPPORT_DIR.exists() else LOCAL_ENV
        
        lines = []
        if env_target.exists():
            with open(env_target, "r") as f:
                lines = f.readlines()
        
        key_found = False
        new_lines = []
        for line in lines:
            if line.startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={api_key.strip()}\n")
                key_found = True
            else:
                new_lines.append(line)
        if not key_found:
            new_lines.append(f"GEMINI_API_KEY={api_key.strip()}\n")

        with open(env_target, "w") as f:
            f.writelines(new_lines)

        cls.GEMINI_API_KEY = api_key.strip()
        os.environ["GEMINI_API_KEY"] = api_key.strip()
