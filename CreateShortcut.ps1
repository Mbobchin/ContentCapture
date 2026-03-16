# Run this if the desktop shortcut wasn't created by setup
$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
$ws = New-Object -ComObject WScript.Shell
$s  = $ws.CreateShortcut("$desktop\ContentCapture.lnk")
$s.TargetPath      = "C:\ContentCapture_v2\ContentCapture.bat"
$s.WorkingDirectory= "C:\ContentCapture_v2"
$s.IconLocation    = "C:\ContentCapture_v2\ContentCapture.ico"
$s.Description     = "ContentCapture v2 — Capture Card Viewer"
$s.Save()
Write-Host "Shortcut created at: $desktop\ContentCapture.lnk"
