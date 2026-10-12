import AppKit
from Foundation import (
    NSObject,
    NSMakeRect,
    NSMakePoint,
    NSMakeSize
)
from AppKit import (
    NSColor,
    NSFont,
    NSPasteboard,
    NSPasteboardTypeString
)
from PyObjCTools import AppHelper
from omni.config import Config
from omni.ui.markdown_parser import markdown_to_attributed_string

class FloatingHUD(AppKit.NSPanel):
    """Refined, borderless floating HUD window."""

    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return True

    def keyDown_(self, event):
        # 53 = Escape
        if event.keyCode() == 53:
            if hasattr(self, 'hud_ref') and self.hud_ref:
                self.hud_ref.hide()
            else:
                self.orderOut_(None)
        # Cmd + C
        elif event.keyCode() == 8 and (event.modifierFlags() & AppKit.NSEventModifierFlagCommand):
            if hasattr(self, 'hud_ref') and self.hud_ref:
                self.hud_ref.copy_to_clipboard()
        else:
            AppKit.objc.super(FloatingHUD, self).keyDown_(event)

class ClickTarget(NSObject):
    hud = None

    def copyClicked_(self, sender):
        if self.hud:
            self.hud.copy_to_clipboard()

    def closeClicked_(self, sender):
        if self.hud:
            self.hud.hide()

class OmniHUD:
    """Raycast-inspired, clean floating panel."""

    def __init__(self, width: int = 700, height: int = 460):
        self.width = width
        self.height = height
        self.raw_markdown_text = ""

        # Center horizontally, upper-third of screen
        screen = AppKit.NSScreen.mainScreen()
        screen_frame = screen.frame() if screen else NSMakeRect(0, 0, 1440, 900)
        pos_x = (screen_frame.size.width - self.width) / 2
        pos_y = screen_frame.size.height - self.height - 110

        rect = NSMakeRect(pos_x, pos_y, self.width, self.height)
        mask = (
            AppKit.NSWindowStyleMaskBorderless |
            AppKit.NSWindowStyleMaskTitled |
            AppKit.NSWindowStyleMaskFullSizeContentView
        )

        self.panel = FloatingHUD.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, mask, AppKit.NSBackingStoreBuffered, False
        )
        self.panel.hud_ref = self
        self.panel.setLevel_(AppKit.NSFloatingWindowLevel)
        self.panel.setMovableByWindowBackground_(True)
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setTitlebarAppearsTransparent_(True)
        self.panel.setTitleVisibility_(AppKit.NSWindowTitleHidden)
        self.panel.setHasShadow_(True)

        self.target = ClickTarget.alloc().init()
        self.target.hud = self

        self._setup_views()

    def _setup_views(self):
        # Frosted glass background
        self.background = AppKit.NSVisualEffectView.alloc().initWithFrame_(
            NSMakeRect(0, 0, self.width, self.height)
        )
        self.background.setMaterial_(AppKit.NSVisualEffectMaterialHUDWindow)
        self.background.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
        self.background.setState_(AppKit.NSVisualEffectStateActive)
        self.background.setWantsLayer_(True)
        self.background.layer().setCornerRadius_(14.0)
        self.background.layer().setMasksToBounds_(True)
        self.background.layer().setBorderWidth_(1.0)
        self.background.layer().setBorderColor_(
            NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.08).CGColor()
        )

        # Header Bar (36px high)
        header_y = self.height - 36
        header_view = AppKit.NSView.alloc().initWithFrame_(
            NSMakeRect(0, header_y, self.width, 36)
        )

        # Brand pill / label
        self.badge = AppKit.NSTextField.alloc().initWithFrame_(
            NSMakeRect(16, 8, 55, 20)
        )
        self.badge.setBezeled_(False)
        self.badge.setDrawsBackground_(False)
        self.badge.setEditable_(False)
        self.badge.setSelectable_(False)
        self.badge.setStringValue_("OMNI")
        self.badge.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, AppKit.NSFontWeightBold))
        self.badge.setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.38, 0.69, 0.94, 1.0))
        header_view.addSubview_(self.badge)

        # Status text
        self.status_label = AppKit.NSTextField.alloc().initWithFrame_(
            NSMakeRect(72, 8, 380, 20)
        )
        self.status_label.setBezeled_(False)
        self.status_label.setDrawsBackground_(False)
        self.status_label.setEditable_(False)
        self.status_label.setSelectable_(False)
        self.status_label.setStringValue_("Ready")
        self.status_label.setFont_(NSFont.systemFontOfSize_weight_(12, AppKit.NSFontWeightRegular))
        self.status_label.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.5))
        header_view.addSubview_(self.status_label)

        # Keyboard shortcuts hint / copy badge (Clickable)
        self.copy_btn = AppKit.NSButton.alloc().initWithFrame_(
            NSMakeRect(self.width - 150, 7, 72, 22)
        )
        self.copy_btn.setTitle_("⌘C Copy")
        self.copy_btn.setBezelStyle_(AppKit.NSBezelStyleInline)
        self.copy_btn.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, AppKit.NSFontWeightRegular))
        self.copy_btn.setTarget_(self.target)
        self.copy_btn.setAction_("copyClicked:")
        header_view.addSubview_(self.copy_btn)

        # Close badge (Clickable)
        self.close_btn = AppKit.NSButton.alloc().initWithFrame_(
            NSMakeRect(self.width - 70, 7, 54, 22)
        )
        self.close_btn.setTitle_("esc")
        self.close_btn.setBezelStyle_(AppKit.NSBezelStyleInline)
        self.close_btn.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, AppKit.NSFontWeightRegular))
        self.close_btn.setTarget_(self.target)
        self.close_btn.setAction_("closeClicked:")
        header_view.addSubview_(self.close_btn)

        self.background.addSubview_(header_view)

        # Divider (1px subtle border)
        divider = AppKit.NSBox.alloc().initWithFrame_(
            NSMakeRect(0, header_y, self.width, 1)
        )
        divider.setBoxType_(AppKit.NSBoxCustom)
        divider.setBorderWidth_(0)
        divider.setFillColor_(NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.06))
        self.background.addSubview_(divider)

        # Content ScrollView (with generous 18px padding)
        scroll_rect = NSMakeRect(16, 14, self.width - 32, self.height - 54)
        self.scroll_view = AppKit.NSScrollView.alloc().initWithFrame_(scroll_rect)
        self.scroll_view.setHasVerticalScroller_(True)
        self.scroll_view.setHasHorizontalScroller_(False)
        self.scroll_view.setAutohidesScrollers_(True)
        self.scroll_view.setDrawsBackground_(False)

        content_size = self.scroll_view.contentSize()
        self.text_view = AppKit.NSTextView.alloc().initWithFrame_(
            NSMakeRect(0, 0, content_size.width, content_size.height)
        )
        self.text_view.setEditable_(False)
        self.text_view.setSelectable_(True)
        self.text_view.setDrawsBackground_(False)
        self.text_view.setTextContainerInset_(NSMakeSize(6, 10))
        self.text_view.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.92))
        self.text_view.setFont_(NSFont.systemFontOfSize_(14))

        self.scroll_view.setDocumentView_(self.text_view)
        self.background.addSubview_(self.scroll_view)

        self.panel.setContentView_(self.background)

    def show(self, status: str = ""):
        def _do_show():
            if status:
                self.set_status(status)
            self.panel.makeKeyAndOrderFront_(None)
            AppKit.NSApp.activateIgnoringOtherApps_(True)
        AppHelper.callAfter(_do_show)

    def hide(self):
        if hasattr(self, 'on_dismiss') and self.on_dismiss:
            try:
                self.on_dismiss()
            except Exception:
                pass

        def _do_hide():
            self.panel.orderOut_(None)
        AppHelper.callAfter(_do_hide)

    def set_status(self, text: str):
        def _update():
            self.status_label.setStringValue_(text)
            if "Listening" in text:
                self.status_label.setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.94, 0.38, 0.38, 1.0))
            elif "Thinking" in text or "Analyzing" in text or "Streaming" in text:
                self.status_label.setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.38, 0.69, 0.94, 1.0))
            else:
                self.status_label.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.5))
        AppHelper.callAfter(_update)

    def set_content(self, markdown_text: str):
        self.raw_markdown_text = markdown_text

        def _update():
            attr_str = markdown_to_attributed_string(markdown_text)
            self.text_view.textStorage().setAttributedString_(attr_str)
        AppHelper.callAfter(_update)

    def append_token(self, token: str):
        self.raw_markdown_text += token

        def _update():
            attr_str = markdown_to_attributed_string(self.raw_markdown_text)
            self.text_view.textStorage().setAttributedString_(attr_str)
            self.text_view.scrollRangeToVisible_(AppKit.NSMakeRange(attr_str.length(), 0))
        AppHelper.callAfter(_update)

    def copy_to_clipboard(self):
        pasteboard = NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        pasteboard.setString_forType_(self.raw_markdown_text, NSPasteboardTypeString)
        
        self.copy_btn.setTitle_("✓ Copied")
        def _reset():
            self.copy_btn.setTitle_("⌘C Copy")
        AppHelper.callLater(1.5, _reset)
