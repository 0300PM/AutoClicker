$root = Split-Path -Parent $PSScriptRoot
$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'AutoClicker.lnk'
if (Test-Path -LiteralPath $lnk) {
    Remove-Item -LiteralPath $lnk -Force
    Write-Host ('   Usunieto skrot: ' + $lnk)
}
$venv = Join-Path $root '.venv'
if (Test-Path -LiteralPath $venv) {
    Remove-Item -LiteralPath $venv -Recurse -Force
    Write-Host '   Usunieto srodowisko .venv'
}
Write-Host '   Program zostal odinstalowany. Pozostale pliki projektu mozesz skasowac recznie.'
Write-Host '   Ustawienia: %APPDATA%\AutoClicker (usun je, jesli chcesz moc wyczyscic wszystko).'
