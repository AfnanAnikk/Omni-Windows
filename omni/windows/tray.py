import threading
from pathlib import Path
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from omni.config import Config

class WindowsTrayApp:
    """Windows notification area system tray menu."""

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.icon = None

    def _create_default_image(self):
        icon_path = Path(__file__).resolve().parent.parent.parent / "resources" / "AppIcon.ico"
        if icon_path.exists():
            try:
                return Image.open(icon_path)
            except Exception:
                pass

        # Fallback generated icon (32x32 blue dot)
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 28, 28], fill=(59, 130, 246), outline=(255, 255, 255))
        return img

    def _on_trigger(self, icon, item):
        self.coordinator.toggle_trigger()

    def _on_exit(self, icon, item):
        self.coordinator.quit()

    def start(self):
        menu = (
            item("Omni: Hold Ctrl + 0", self._on_trigger, default=True),
            item("Trigger Ask", self._on_trigger),
            pystray.Menu.SEPARATOR,
            item("Exit Omni", self._on_exit)
        )
        self.icon = pystray.Icon("Omni", self._create_default_image(), "Omni - Ambient AI", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
