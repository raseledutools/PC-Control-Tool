[Setup]
AppName=Ras PC Care
AppVersion=1.0
DefaultDirName={autopf}\RasPcCare
DefaultGroupName=Ras PC Care
OutputDir=dist
OutputBaseFilename=RasPcCare_Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Ras PC Care"; Filename: "{app}\main.exe"
Name: "{autodesktop}\Ras PC Care"; Filename: "{app}\main.exe"

[Run]
Filename: "{app}\main.exe"; Description: "Launch Ras PC Care"; Flags: nowait postinstall skipifsilent
