param([Parameter(Mandatory=$true)][string]$Programme)
$ErrorActionPreference = 'Stop'
try {
 $cle = 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64'
 $runtime = Get-ItemProperty $cle -ErrorAction SilentlyContinue
 if ($runtime.Installed -eq 1 -and $runtime.Major -ge 14 -and $runtime.Minor -ge 44) { exit 0 }
 # Le programme officiel Microsoft affiche la demande Windows si nécessaire.
 $processus = Start-Process -FilePath $Programme -ArgumentList '/install','/passive','/norestart' -Verb RunAs -Wait -PassThru
 if ($processus.ExitCode -in @(0,1638,3010)) { exit 0 }
 exit 1
} catch { exit 1 }
