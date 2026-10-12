import AppKit
from Foundation import NSMakeRect, NSColor, NSFont
from PyObjCTools import AppHelper

class MicIndicator:
    """Discreet, Siri-style ambient pill indicator in the top-right corner.
    
    Clean, pure rounded pill with zero rectangular border artifacts or window frames.
    """

    def __init__(self):
        self.width = 132
        self.height = 38

        # Pure borderless mask with NO window chrome or full-size content view
        mask = AppKit.NSWindowStyleMaskBorderless

        rect = self._compute_rect()
        self.panel = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, mask, AppKit.NSBackingStoreBuffered, False
        )
        # Highest window level so it floats above full-screen apps and all windows
        self.panel.setLevel_(AppKit.NSScreenSaverWindowLevel)
        self.panel.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
            AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary |
            AppKit.NSWindowCollectionBehaviorStationary
        )
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        # Disable window-level shadow so macOS does not draw a rectangular border/shadow
        self.panel.setHasShadow_(False)
        self.panel.setHidesOnDeactivate_(False)
        self.panel.setFloatingPanel_(True)
        self.panel.setIgnoresMouseEvents_(True)

        # Pure layer-backed rounded pill view (masksToBounds=True guarantees 100% transparent corners)
        self.bg = AppKit.NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, self.width, self.height)
        )
        self.bg.setWantsLayer_(True)
        self.bg.layer().setCornerRadius_(19.0)
        self.bg.layer().setMasksToBounds_(True)
        self.bg.layer().setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.11, 0.13, 0.18, 0.95).CGColor()
        )
        self.bg.layer().setBorderWidth_(1.5)

        # Spinner (Processing state)
        self.spinner = AppKit.NSProgressIndicator.alloc().initWithFrame_(
            NSMakeRect(14, 11, 16, 16)
        )
        self.spinner.setStyle_(AppKit.NSProgressIndicatorStyleSpinning)
        self.spinner.setControlSize_(AppKit.NSControlSizeSmall)
        self.bg.addSubview_(self.spinner)

        # Icon / Dot (Listening state)
        self.icon_label = AppKit.NSTextField.alloc().initWithFrame_(
            NSMakeRect(12, 10, 22, 18)
        )
        self.icon_label.setBezeled_(False)
        self.icon_label.setDrawsBackground_(False)
        self.icon_label.setEditable_(False)
        self.icon_label.setSelectable_(False)
        self.icon_label.setStringValue_("🔴")
        self.icon_label.setFont_(NSFont.systemFontOfSize_(12))
        self.bg.addSubview_(self.icon_label)

        # Text label ("Listening..." / "Thinking...")
        self.text_label = AppKit.NSTextField.alloc().initWithFrame_(
            NSMakeRect(34, 10, 90, 18)
        )
        self.text_label.setBezeled_(False)
        self.text_label.setDrawsBackground_(False)
        self.text_label.setEditable_(False)
        self.text_label.setSelectable_(False)
        self.text_label.setFont_(NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightBold))
        self.bg.addSubview_(self.text_label)

        self.panel.setContentView_(self.bg)

    def _compute_rect(self):
        screen = AppKit.NSScreen.mainScreen()
        vf = screen.visibleFrame() if screen else NSMakeRect(0, 0, 1440, 900)
        # Position 20px from right, 14px below the menu bar
        pos_x = vf.origin.x + vf.size.width - self.width - 20
        pos_y = vf.origin.y + vf.size.height - self.height - 14
        return NSMakeRect(pos_x, pos_y, self.width, self.height)

    def start_listening(self):
        """Displays indicator in active listening state (holding hotkey)."""
        def _do():
            self.panel.setFrame_display_(self._compute_rect(), True)
            self.spinner.setHidden_(True)
            self.spinner.stopAnimation_(None)
            self.icon_label.setHidden_(False)
            self.icon_label.setStringValue_("🔴")
            self.text_label.setStringValue_("Listening...")
            self.text_label.setTextColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.4, 0.4, 1.0)
            )
            self.bg.layer().setBorderColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(0.98, 0.45, 0.45, 0.85).CGColor()
            )
            self.panel.orderFrontRegardless()
        AppHelper.callAfter(_do)

    def start_processing(self):
        """Transitions indicator to thinking/processing state (released hotkey, waiting for Gemini)."""
        def _do():
            self.panel.setFrame_display_(self._compute_rect(), True)
            self.icon_label.setHidden_(True)
            self.spinner.setHidden_(False)
            self.spinner.startAnimation_(None)
            self.text_label.setStringValue_("Thinking...")
            self.text_label.setTextColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(0.45, 0.78, 1.0, 1.0)
            )
            self.bg.layer().setBorderColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(0.65, 0.45, 1.0, 0.85).CGColor()
            )
            self.panel.orderFrontRegardless()
        AppHelper.callAfter(_do)

    def show(self):
        self.start_listening()

    def hide(self):
        """Hides the top-right indicator."""
        def _do():
            self.spinner.stopAnimation_(None)
            self.panel.orderOut_(None)
        AppHelper.callAfter(_do)
