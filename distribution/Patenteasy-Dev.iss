#define MyAppVersion "0.4.5.1"
[Setup]
AppId={{F975B994-BF4D-4AE7-9618-909F16BD8102}
AppName=Patenteasy TEST
AppVersion={#MyAppVersion}
AppPublisher=ska_987
AppSupportURL=mailto:sav.centreprotech@proton.me
DefaultDirName={localappdata}\Programs\PatenteasyLocal-DEV
DefaultGroupName=Patenteasy TEST
PrivilegesRequired=lowest
DisableDirPage=yes
UsePreviousAppDir=no
OutputDir=sortie
OutputBaseFilename=Patenteasy-Windows-TEST-Installation
Compression=lzma2
SolidCompression=yes
LicenseFile=..\LICENSE
[Files]
Source: "..\dist\Patenteasy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Patenteasy TEST"; Filename: "{app}\Patenteasy.exe"
Name: "{autodesktop}\Patenteasy TEST"; Filename: "{app}\Patenteasy.exe"
[Run]
Filename: "{app}\Patenteasy.exe"; Description: "Ouvrir Patenteasy TEST"; Flags: nowait postinstall skipifsilent

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if CompareText(RemoveBackslashUnlessRoot(ExpandFileName(WizardDirValue)), RemoveBackslashUnlessRoot(ExpandConstant('{localappdata}\Programs\PatenteasyLocal'))) = 0 then
    Result := 'Choisissez un dossier de test distinct de Patenteasy habituel.';
end;
