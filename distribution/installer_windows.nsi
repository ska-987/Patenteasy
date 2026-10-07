; SPDX-License-Identifier: GPL-3.0-or-later
Unicode true
Icon "..\static\patenteasy.ico"
!include "MUI2.nsh"
!include "x64.nsh"
!ifndef PROGRAMME
!error "Fournir /DPROGRAMME=chemin_du_paquet"
!endif
!ifndef SORTIE
!define SORTIE "Patenteasy-Windows-0.3.7-Installation.exe"
!endif
Name "Patenteasy"
OutFile "${SORTIE}"
InstallDir "$LOCALAPPDATA\Programs\PatenteasyLocal"
RequestExecutionLevel user
SetCompressor /SOLID lzma
VIProductVersion "0.3.7.0"
VIAddVersionKey "ProductName" "Patenteasy"
VIAddVersionKey "FileDescription" "Installation locale Patenteasy"
VIAddVersionKey "FileVersion" "0.3.7"
VIAddVersionKey "LegalCopyright" "ska_987 · GNU GPL v3+"
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "French"
Section "Patenteasy"
  SetShellVarContext current
  SetOverwrite on
  ; L'installation ne supprime et ne remplace aucune base d'utilisateur.
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File "windows/verifier_arret.ps1"
  nsExec::ExecToStack '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\verifier_arret.ps1" -Installation "$INSTDIR"'
  Pop $0
  Pop $1
  StrCmp $0 "0" continuer
  MessageBox MB_OK|MB_ICONEXCLAMATION "Fermez la fenêtre Patenteasy (et tout ancien terminal encore ouvert) puis relancez cette installation. Si PowerShell est indisponible, utilisez le paquet ZIP."
  Abort
  continuer:
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "Patenteasy nécessite Windows 64 bits."
    Abort
  ${EndIf}
  SetOutPath "$PLUGINSDIR"
  File "windows/installer_composant.ps1"
  File /oname=vc_redist.x64.exe "${PROGRAMME}\..\vc_redist.x64.exe"
  DetailPrint "Vérification du composant Microsoft nécessaire à Qt..."
  nsExec::ExecToStack '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\installer_composant.ps1" -Programme "$PLUGINSDIR\vc_redist.x64.exe"'
  Pop $0
  Pop $1
  StrCmp $0 "0" composants_ok
  MessageBox MB_OK|MB_ICONEXCLAMATION "Le composant Microsoft requis n'a pas pu être installé. Autorisez son installation puis relancez Patenteasy Setup. Vos données sont conservées."
  Abort
  composants_ok:
  ; Interface Qt native : aucune dépendance Microsoft Edge/WebView2.
  SetOutPath "$INSTDIR"
  File /r "${PROGRAMME}\*"
  ; Supprimer explicitement les raccourcis de la précédente édition.
  Delete "$DESKTOP\Patenteasy.lnk"
  Delete "$SMPROGRAMS\Patenteasy\Patenteasy.lnk"
  CreateDirectory "$SMPROGRAMS\Patenteasy"
  ClearErrors
  CreateShortcut "$SMPROGRAMS\Patenteasy\Patenteasy.lnk" "$INSTDIR\runtime\pythonw.exe" '$\"$INSTDIR\app\application_windows.py$\"' '$INSTDIR\app\static\patenteasy.ico' 0
  CreateShortcut "$DESKTOP\Patenteasy.lnk" "$INSTDIR\runtime\pythonw.exe" '$\"$INSTDIR\app\application_windows.py$\"' '$INSTDIR\app\static\patenteasy.ico' 0
  IfErrors raccourcis_echec raccourcis_ok
  raccourcis_echec:
  MessageBox MB_OK|MB_ICONSTOP "Impossible de remplacer les raccourcis Patenteasy. Fermez leurs propriétés et relancez cet installateur."
  Abort
  raccourcis_ok:
  ; Invalider l'affichage de l'ancien raccourci dans Explorer.
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
  WriteUninstaller "$INSTDIR\Desinstaller.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PatenteasyLocal" "DisplayName" "Patenteasy"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PatenteasyLocal" "DisplayVersion" "0.3.7"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PatenteasyLocal" "Publisher" "ska_987"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PatenteasyLocal" "UninstallString" '$\"$INSTDIR\Desinstaller.exe$\"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PatenteasyLocal" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PatenteasyLocal" "NoRepair" 1
SectionEnd
Section "Uninstall"
  MessageBox MB_YESNO "Fermez Patenteasy avant de désinstaller. Vos données personnelles seront conservées. Continuer ?" IDYES supprimer
  Abort
  supprimer:
  Delete "$SMPROGRAMS\Patenteasy\Patenteasy.lnk"
  RMDir "$SMPROGRAMS\Patenteasy"
  Delete "$DESKTOP\Patenteasy.lnk"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PatenteasyLocal"
  RMDir /r "$INSTDIR\app"
  RMDir /r "$INSTDIR\runtime"
  Delete "$INSTDIR\Patenteasy.cmd"
  Delete "$INSTDIR\Desinstaller.exe"
  RMDir "$INSTDIR"
SectionEnd
