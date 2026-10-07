param([Parameter(Mandatory=$true)][string]$Installation)
$ErrorActionPreference = 'Stop'
try {
    $actifs = Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($Installation, [System.StringComparison]::OrdinalIgnoreCase)
    }
    if ($actifs) { exit 1 }
    exit 0
} catch { exit 2 }
