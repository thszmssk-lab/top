$dir = $PSScriptRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $desktop '영상 컨트롤타워.lnk'
$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
$s.TargetPath = Join-Path $dir 'start.bat'
$s.WorkingDirectory = $dir
$s.IconLocation = (Join-Path $dir 'icon.ico') + ',0'
$s.WindowStyle = 7
$s.Description = '영상 컨트롤타워 실행'
$s.Save()
Write-Host "바탕화면에 '영상 컨트롤타워' 아이콘을 만들었습니다: $lnk"
