#define MyAppVersion "0.3.8"
[Setup]
AppId={{22CBB249-971D-4915-A2CC-59A2663E80BD}
AppName=Patenteasy
AppVersion={#MyAppVersion}
AppPublisher=ska_987
AppSupportURL=mailto:sav.centreprotech@proton.me
DefaultDirName={localappdata}\Programs\PatenteasyLocal
DefaultGroupName=Patenteasy
PrivilegesRequired=lowest
OutputDir=sortie
OutputBaseFilename=Patenteasy-Windows-{#MyAppVersion}-Installation
Compression=lzma2
SolidCompression=yes
LicenseFile=..\LICENSE
[Files]
Source: "..\dist\Patenteasy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Patenteasy"; Filename: "{app}\Patenteasy.exe"
Name: "{autodesktop}\Patenteasy"; Filename: "{app}\Patenteasy.exe"
[Run]
Filename: "{app}\Patenteasy.exe"; Description: "Ouvrir Patenteasy"; Flags: nowait postinstall skipifsilent
