import ctypes
from pathlib import Path

# Load native Carbon hotkey library
DYLIB_PATH = Path(__file__).resolve().parent / "native" / "libhotkey.dylib"
CALLBACK_TYPE = ctypes.CFUNCTYPE(None)

class HotkeyListener:
    """Carbon-based system-wide hotkey listener for Cmd + 0 (Push-to-Talk)."""

    def __init__(self, on_trigger_start, on_trigger_stop):
        self.on_trigger_start = on_trigger_start
        self.on_trigger_stop = on_trigger_stop
        self._lib = None
        self._cb_press = None
        self._cb_release = None

    def start(self):
        """Registers global Cmd + 0 shortcut via Carbon."""
        if not DYLIB_PATH.exists():
            raise FileNotFoundError(f"Native library not found at: {DYLIB_PATH}")

        self._lib = ctypes.CDLL(str(DYLIB_PATH))

        def _press():
            self.on_trigger_start()

        def _release():
            self.on_trigger_stop()

        self._cb_press = CALLBACK_TYPE(_press)
        self._cb_release = CALLBACK_TYPE(_release)

        # KeyCode 29 is '0'
        # Modifier 0x100 is cmdKey in Carbon
        status = self._lib.init_carbon_hotkey(29, 0x100, self._cb_press, self._cb_release)
        if status == 0:
            print("[Omni] Global Carbon Cmd + 0 listener active (Push-to-Talk ready).")
        else:
            print(f"[Omni] Failed to register Carbon hotkey, status: {status}")

    def stop(self):
        pass
