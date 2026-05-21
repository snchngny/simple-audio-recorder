#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

echo "Installing PyInstaller..."
pip install pyinstaller

echo "Configuring PyInstaller and building .app bundle..."
# --windowed removes the terminal backdrop, making it a pure GUI app
# --noconfirm overwrites any existing build folders
pyinstaller --name "SimpleAudioRecorder" --windowed --noconfirm main.py

echo "Adding Microphone Permission to Info.plist..."
# macOS strictly requires this string in the .app bundle to allow mic usage
plutil -insert NSMicrophoneUsageDescription -string "録音機能のためにマイクへアクセスします。" dist/SimpleAudioRecorder.app/Contents/Info.plist

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
xattr -cr dist/SimpleAudioRecorder.app
codesign --force --deep --sign - --entitlements entitlements.plist dist/SimpleAudioRecorder.app

echo "Build complete. App is located in dist/SimpleAudioRecorder.app"
