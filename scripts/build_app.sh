#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="Omni"
DIST_DIR="$SCRIPT_DIR/dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

echo "Building $APP_NAME.app..."

# 1. Clean previous build
rm -rf "$APP_BUNDLE"
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR/app"

# 2. Info.plist (no icon requirements, pure LSUIElement)
cat << 'EOF' > "$CONTENTS_DIR/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Omni</string>
    <key>CFBundleDisplayName</key>
    <string>Omni</string>
    <key>CFBundleIdentifier</key>
    <string>com.afnan.omni</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>Omni</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSUIElement</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Omni needs microphone access for voice questions.</string>
    <key>NSScreenCaptureUsageDescription</key>
    <string>Omni needs screen recording access to inspect the screen.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>Omni requires accessibility permissions for Right Shift + O hotkey.</string>
</dict>
</plist>
EOF

# 3. Copy Icon if present
if [ -f "resources/AppIcon.icns" ]; then
    cp "resources/AppIcon.icns" "$RESOURCES_DIR/AppIcon.icns"
fi

# 4. Compile native Carbon hotkey library
clang -dynamiclib -framework Carbon omni/native/hotkey.c -o omni/native/libhotkey.dylib

# 5. Copy application code
cp -R omni "$RESOURCES_DIR/app/"
cp main.py "$RESOURCES_DIR/app/"
if [ -f .env ]; then
    cp .env "$RESOURCES_DIR/app/"
fi

# 4. Launcher script
cat << EOF > "$MACOS_DIR/Omni"
#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export PYTHONUNBUFFERED=1

BUNDLE_DIR="\$(cd "\$(dirname "\$0")/.." && pwd)"
RESOURCES_DIR="\$BUNDLE_DIR/Resources"
APP_DIR="\$RESOURCES_DIR/app"

LOG_FILE="\$HOME/Library/Logs/Omni.log"
if ! touch "\$LOG_FILE" 2>/dev/null; then
    mkdir -p "/tmp/omni"
    LOG_FILE="/tmp/omni/app.log"
fi

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

echo "=== Omni Launched: \$(date) ===" >> "\$LOG_FILE" 2>/dev/null || true
exec "\$VENV_PYTHON" "\$APP_DIR/main.py" "\$@" >> "\$LOG_FILE" 2>&1
EOF

chmod +x "$MACOS_DIR/Omni"

echo "Built: $APP_BUNDLE"

# 5. Install to /Applications
rm -rf /Applications/Omni.app 2>/dev/null || true
cp -R "$APP_BUNDLE" /Applications/Omni.app 2>/dev/null || cp -R "$APP_BUNDLE" "$HOME/Applications/Omni.app"
echo "Installed to /Applications/Omni.app"
