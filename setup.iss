[Setup]
AppName=Rasel Web Tools PRO
AppVersion=1.0
DefaultDirName={autopf}\RaselWebTools
DefaultGroupName=Rasel Web Tools PRO
OutputDir=dist
OutputBaseFilename=Rasel_WebTools_Setup
Compression=lzma
SolidCompression=yes

[Files]
; Source শুধু main.exe থাকবে, কারণ আমরা রানারকে dist ফোল্ডারে নিয়ে যাব
Source: "main.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Rasel Web Tools"; Filename: "{app}\main.exe"
Name: "{autodesktop}\Rasel Web Tools"; Filename: "{app}\main.exe"

[Run]
Filename: "{app}\main.exe"; Description: "Launch Rasel Web Tools PRO"; Flags: nowait postinstall skipifsilent
