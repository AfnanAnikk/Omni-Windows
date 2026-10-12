import AppKit
import subprocess
from Foundation import NSObject
from ApplicationServices import AXIsProcessTrusted
from PyObjCTools import AppHelper

class MenuTarget(NSObject):
    app_coordinator = None

    def triggerClicked_(self, sender):
        if self.app_coordinator:
            self.app_coordinator.toggle_trigger()

    def grantPermClicked_(self, sender):
        subprocess.Popen([
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        ])

    def quitClicked_(self, sender):
        AppKit.NSApp.terminate_(self)

class StatusBarApp:
    """Menu bar controller for Omni with permission status."""

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.status_bar = AppKit.NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(
            AppKit.NSVariableStatusItemLength
        )
        
        button = self.status_item.button()
        button.setTitle_("Omni")

        self.target = MenuTarget.alloc().init()
        self.target.app_coordinator = coordinator

        self._build_menu()

    def _build_menu(self):
        menu = AppKit.NSMenu.alloc().init()

        trigger_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Ask Omni (Cmd + 0)", "triggerClicked:", ""
        )
        trigger_item.setTarget_(self.target)
        menu.addItem_(trigger_item)

        # Show Accessibility warning if missing
        if not AXIsProcessTrusted():
            perm_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "⚠️ Enable Accessibility in System Settings...", "grantPermClicked:", ""
            )
            perm_item.setTarget_(self.target)
            menu.addItem_(perm_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Omni", "quitClicked:", "q"
        )
        quit_item.setTarget_(self.target)
        menu.addItem_(quit_item)

        self.status_item.setMenu_(menu)

    def set_status_text(self, text: str):
        def _update():
            button = self.status_item.button()
            if button:
                button.setTitle_(text)
        AppHelper.callAfter(_update)
