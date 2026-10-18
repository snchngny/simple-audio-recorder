#ifndef AppVersion
  #error AppVersion is required
#endif
[Setup]
AppId={{DAFF385C-39A5-47B7-AF1C-E61EBCA75455}
AppName=Simple Sample Recorder
AppVersion={#AppVersion}
AppPublisher=snchngny
AppPublisherURL=https://github.com/snchngny/simple-audio-recorder
DefaultDirName={localappdata}\Programs\SimpleAudioRecorder
DefaultGroupName=Simple Sample Recorder
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=SimpleAudioRecorder-v{#AppVersion}-windows-x64-setup
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\SimpleAudioRecorder.exe
[Files]
Source: "..\dist\SimpleAudioRecorder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Simple Sample Recorder"; Filename: "{app}\SimpleAudioRecorder.exe"
[Run]
Filename: "{app}\SimpleAudioRecorder.exe"; Description: "Simple Sample Recorder を起動"; Flags: nowait postinstall skipifsilent
