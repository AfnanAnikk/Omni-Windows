#include <Carbon/Carbon.h>
#include <stdio.h>

typedef void (*HotkeyCallback)(void);

static HotkeyCallback g_on_press = NULL;
static HotkeyCallback g_on_release = NULL;
static EventHotKeyRef g_hotkey_ref = NULL;

static OSStatus hotkey_handler(EventHandlerCallRef nextHandler, EventRef theEvent, void *userData) {
    UInt32 event_kind = GetEventKind(theEvent);
    if (event_kind == kEventHotKeyPressed) {
        if (g_on_press) g_on_press();
    } else if (event_kind == kEventHotKeyReleased) {
        if (g_on_release) g_on_release();
    }
    return noErr;
}

int init_carbon_hotkey(uint32_t keycode, uint32_t modifiers, HotkeyCallback on_press, HotkeyCallback on_release) {
    g_on_press = on_press;
    g_on_release = on_release;

    EventTypeSpec eventTypes[2];
    eventTypes[0].eventClass = kEventClassKeyboard;
    eventTypes[0].eventKind = kEventHotKeyPressed;
    eventTypes[1].eventClass = kEventClassKeyboard;
    eventTypes[1].eventKind = kEventHotKeyReleased;

    InstallApplicationEventHandler(&hotkey_handler, 2, eventTypes, NULL, NULL);

    EventHotKeyID hotkeyID;
    hotkeyID.signature = 'OMNI';
    hotkeyID.id = 1;

    // Release any previous hotkey
    if (g_hotkey_ref) {
        UnregisterEventHotKey(g_hotkey_ref);
        g_hotkey_ref = NULL;
    }

    OSStatus status = RegisterEventHotKey(keycode, modifiers, hotkeyID, GetApplicationEventTarget(), 0, &g_hotkey_ref);
    return (status == noErr) ? 0 : (int)status;
}
