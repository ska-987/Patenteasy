$ErrorActionPreference = 'Stop'
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$destination = Join-Path $env:LOCALAPPDATA 'Programs\PatenteasyLocal'
if (Test-Path $destination) {
    $actifs = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($destination, [System.StringComparison]::OrdinalIgnoreCase) }
    if ($actifs) { throw 'Fermez Patenteasy avant de mettre à jour le programme.' }
}
# L'interface Windows est maintenant Qt/PySide6 : aucun composant Edge/WebView2 n'est requis.
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Copy-Item (Join-Path $source 'programme\*') $destination -Recurse -Force
$shell = New-Object -ComObject WScript.Shell
$bureau = [Environment]::GetFolderPath('Desktop')
$menu = Join-Path ([Environment]::GetFolderPath('Programs')) 'Patenteasy'
New-Item -ItemType Directory -Force -Path $menu | Out-Null
foreach ($dossier in @($bureau,$menu)) {
    $cheminRaccourci = Join-Path $dossier 'Patenteasy.lnk'
    if (Test-Path $cheminRaccourci) { Remove-Item $cheminRaccourci -Force }
    $raccourci = $shell.CreateShortcut($cheminRaccourci)
    $raccourci.TargetPath = Join-Path $destination 'runtime\pythonw.exe'
    $raccourci.Arguments = '"' + (Join-Path $destination 'app\application_windows.py') + '"'
    $raccourci.WorkingDirectory = $destination
    $raccourci.IconLocation = (Join-Path $destination 'app\static\patenteasy.ico') + ',0'
    $raccourci.Save()
}
Write-Host 'Installation terminee. Raccourcis disponibles sur le bureau et dans le menu Demarrer.'
Write-Host 'Interface Qt native : aucun navigateur ni WebView2 requis.'
Write-Host 'Donnees conservees dans %LOCALAPPDATA%\PatenteasyLocal\data ; aucune base existante remplacee.'
