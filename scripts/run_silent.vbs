Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run Chr(34) & strPath & "\start_backend.bat" & Chr(34), 0, False
WshShell.Run Chr(34) & strPath & "\start_tunnel.bat" & Chr(34), 0, False
Set WshShell = Nothing
