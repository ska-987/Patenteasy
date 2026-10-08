Option Explicit
Dim shell, files, root, exe, local
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
local = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
exe = local & "\Programs\PatenteasyLocal\Patenteasy.exe"
If Not files.FileExists(exe) Then
    MsgBox "Installez Patenteasy 0.3.9 avec l'installeur complet avant de preparer la publication.", 48, "Patenteasy"
    WScript.Quit 1
End If
shell.Run Chr(34) & exe & Chr(34) & " --prepare-publication " & Chr(34) & root & Chr(34), 1, True
