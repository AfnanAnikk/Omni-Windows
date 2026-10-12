import threading
from pynput import keyboard
from omni.config import Config

class WindowsHotkeyListener:
    """Windows global Push-to-Talk hotkey listener using pynput.
    
    Default trigger: Hold Ctrl + 0 to speak, release to answer.
    """

    def __init__(self, on_trigger_start, on_trigger_stop):
        self.on_trigger_start = on_trigger_start
        self.on_trigger_stop = on_trigger_stop
        self._ctrl_down = False
        self._key_down = False
        self._is_active = False
        self._listener = None

    def _on_press(self, key):
        # Check Ctrl key
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_down = True
            return

        # Check '0' key
        is_zero = False
        if hasattr(key, 'char') and key.char == '0':
            is_zero = True
        elif hasattr(key, 'vk') and key.vk in (48, 96): # 48 is '0', 96 is Numpad '0'
            is_zero = True

        if is_zero and self._ctrl_down and not self._is_active:
            self._is_active = True
            self._key_down = True
            print("[WindowsHotkey] 🎙️ Push-to-Talk activated (Ctrl + 0 pressed)")
            self.on_trigger_start()

    def _on_release(self, key):
        # Releasing Ctrl or '0' ends the push-to-talk session
        is_ctrl = key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
        is_zero = False
        if hasattr(key, 'char') and key.char == '0':
            is_zero = True
        elif hasattr(key, 'vk') and key.vk in (48, 96):
            is_zero = True

        if is_ctrl:
            self._ctrl_down = False
            if self._is_active:
                self._is_active = False
                print("[WindowsHotkey] ⚡ Push-to-Talk released (Ctrl released)")
                self.on_trigger_stop()

        if is_zero:
            self._key_down = False
            if self._is_active:
                self._is_active = False
                print("[WindowsHotkey] ⚡ Push-to-Talk released (0 released)")
                self.on_trigger_stop()

    def start(self):
        """Starts background global keyboard listener."""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.daemon = True
        self._listener.start()
        print("[WindowsHotkey] Global Ctrl + 0 Push-to-Talk listener active.")

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
