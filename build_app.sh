#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

APP_NAME="SimpleAudioRecorder"
APP_BUNDLE="dist/${APP_NAME}.app"
VERSION_FILE="VERSION"
APP_VERSION="$(tr -d '[:space:]' < "${VERSION_FILE}")"
BUILD_NUMBER="${BUILD_NUMBER:-$(git rev-list --count HEAD 2>/dev/null || echo 1)}"
RELEASE_ZIP="dist/${APP_NAME}-v${APP_VERSION}-mac.zip"

set_plist_value() {
    local key="$1"
    local type="$2"
    local value="$3"
    local plist="${APP_BUNDLE}/Contents/Info.plist"

    /usr/libexec/PlistBuddy -c "Set :${key} ${value}" "${plist}" 2>/dev/null \
        || /usr/libexec/PlistBuddy -c "Add :${key} ${type} ${value}" "${plist}"
}

source venv/bin/activate

echo "Installing PyInstaller..."
pip install pyinstaller

echo "Building ${APP_NAME} v${APP_VERSION} (${BUILD_NUMBER})..."
# --windowed removes the terminal backdrop, making it a pure GUI app
# --noconfirm overwrites any existing build folders
pyinstaller --name "${APP_NAME}" --windowed --noconfirm main.py

echo "Updating Info.plist..."
# macOS strictly requires this string in the .app bundle to allow mic usage
set_plist_value "NSMicrophoneUsageDescription" "string" "録音機能のためにマイクへアクセスします。"
set_plist_value "CFBundleShortVersionString" "string" "${APP_VERSION}"
set_plist_value "CFBundleVersion" "string" "${BUILD_NUMBER}"

echo "Applying deep code signature with Audio Input Entitlements..."
cat << 'EOF' > entitlements.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.device.audio-input</key>
    <true/>
</dict>
</plist>
EOF
xattr -cr "${APP_BUNDLE}"
codesign --force --deep --sign - --entitlements entitlements.plist "${APP_BUNDLE}"

echo "Creating release zip..."
rm -f "${RELEASE_ZIP}"
ditto -c -k --keepParent "${APP_BUNDLE}" "${RELEASE_ZIP}"

echo "Build complete."
echo "App: ${APP_BUNDLE}"
echo "Release zip: ${RELEASE_ZIP}"
