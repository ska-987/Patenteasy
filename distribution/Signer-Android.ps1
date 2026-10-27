# SPDX-License-Identifier: GPL-3.0-or-later
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Windows.Forms
    if (-not $env:PATENTEASY_KEYSTORE) {
        $choix = New-Object System.Windows.Forms.OpenFileDialog
        $choix.Title = 'Choisir la clé Android originale Patenteasy (fichier JKS)'
        $choix.Filter = 'Clé Android (*.jks;*.keystore)|*.jks;*.keystore|Tous les fichiers (*.*)|*.*'
        if ($choix.ShowDialog() -ne 'OK') { throw 'Signature annulée.' }
        $env:PATENTEASY_KEYSTORE = $choix.FileName
    }
    if (-not $env:PATENTEASY_KEY_ALIAS) { $env:PATENTEASY_KEY_ALIAS = 'ska987' }
    if (-not $env:PATENTEASY_KEY_PASSWORD) {
        $secret = Read-Host 'Mot de passe de la clé Android (différent du mot de passe License Manager)' -AsSecureString
        $env:PATENTEASY_KEY_PASSWORD = [System.Net.NetworkCredential]::new('', $secret).Password
    }
    if ($env:JAVA_HOME -and -not $env:PATENTEASY_JAVA) { $env:PATENTEASY_JAVA = Join-Path $env:JAVA_HOME 'bin\java.exe' }
    $python = 'python'
    if (Get-Command py -ErrorAction SilentlyContinue) { $python = 'py' }
    & $python (Join-Path $PSScriptRoot 'sources\distribution\signer_android_local.py') $PSScriptRoot
    if ($LASTEXITCODE -ne 0) { throw 'Signature échouée. Ne pas utiliser le fichier A-SIGNER sur le téléphone.' }
    Write-Host 'Terminé : transférez Patenteasy-Android-0.4.5.1.apk sur le téléphone puis ouvrez-le pour mettre à jour.'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    Remove-Item Env:PATENTEASY_KEY_PASSWORD -ErrorAction SilentlyContinue
}
