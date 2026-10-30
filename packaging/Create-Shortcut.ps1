$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) {
    $found = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($null -eq $found) {
        Write-Host '   Nie znaleziono pythonw.exe - skrot nie zostal utworzony.'
        exit 0
    }
    $pythonw = $found.Source
}
$target = Join-Path $root 'app.py'
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $desktop 'AutoClicker.lnk'))
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = '"' + $target + '"'
$shortcut.WorkingDirectory = $root
$icon = Join-Path $root 'assets\icon.ico'
if (Test-Path -LiteralPath $icon) { $shortcut.IconLocation = $icon }
$shortcut.Description = 'AutoClicker - autoclicker ze skrótem klawiszowym'
$shortcut.Save()
Write-Host ("   Utworzono skrot: " + (Join-Path $desktop 'AutoClicker.lnk'))
