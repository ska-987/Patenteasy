# SPDX-License-Identifier: GPL-3.0-or-later
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
function Secret($nom, $titre) {
    if (-not [Environment]::GetEnvironmentVariable($nom)) {
        $s = Read-Host $titre -AsSecureString
        [Environment]::SetEnvironmentVariable($nom, [System.Net.NetworkCredential]::new('', $s).Password, 'Process')
    }
}
function Texte($nom, $titre) {
    if (-not [Environment]::GetEnvironmentVariable($nom)) {
        [Environment]::SetEnvironmentVariable($nom, (Read-Host $titre).Trim(), 'Process')
    }
}
try {
    if (-not $env:PATENTEASY_KEYSTORE) {
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = 'Choisir la clé Android originale de Patenteasy'
        $dialog.Filter = 'Clé Android (*.jks;*.keystore)|*.jks;*.keystore|Tous les fichiers (*.*)|*.*'
        if ($dialog.ShowDialog() -ne 'OK') { throw 'Publication annulée, aucune clé choisie.' }
        $env:PATENTEASY_KEYSTORE = $dialog.FileName
    }
    Texte 'PATENTEASY_KEY_ALIAS' 'Alias de la clé Android originale'
    Secret 'PATENTEASY_KEY_PASSWORD' 'Mot de passe de la clé Android'
    Texte 'CLOUDFLARE_ACCOUNT_ID' 'Identifiant du compte Cloudflare'
    Texte 'R2_ACCESS_KEY_ID' 'Identifiant d’accès R2 au bucket patenteasy-releases'
    Secret 'R2_SECRET_ACCESS_KEY' 'Secret d’accès R2'
    if ($env:JAVA_HOME -and -not $env:PATENTEASY_JAVA) { $env:PATENTEASY_JAVA = Join-Path $env:JAVA_HOME 'bin\java.exe' }
    $python = 'python'
    if (Get-Command py -ErrorAction SilentlyContinue) { $python = 'py' }
    $runtime = Join-Path $env:LOCALAPPDATA 'ska_987\publication-patenteasy\venv041'
    if (-not (Test-Path (Join-Path $runtime 'Scripts\python.exe'))) {
        & $python -m venv $runtime
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 ou supérieur est nécessaire.' }
    }
    $python = Join-Path $runtime 'Scripts\python.exe'
    & $python -m pip install --disable-pip-version-check 'cryptography>=43' 'boto3>=1.35' certifi
    if ($LASTEXITCODE -ne 0) { throw 'Installation des dépendances interrompue.' }
    & $python (Join-Path $PSScriptRoot 'sources\distribution\publier_automatique.py') $PSScriptRoot --signer-android
    if ($LASTEXITCODE -ne 0) { throw 'Publication interrompue. Consultez le message ci-dessus.' }
    Write-Host 'Publication terminée : Windows et Android bêta 0.4.1.'
} finally {
    Remove-Item Env:PATENTEASY_KEY_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:R2_SECRET_ACCESS_KEY -ErrorAction SilentlyContinue
}
