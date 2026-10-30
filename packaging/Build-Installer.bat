@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
title Budowanie instalatora AutoClicker

call packaging\Build-EXE.bat
if errorlevel 1 exit /b 1

set "ISCC="
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
    if exist "%%~P" set "ISCC=%%~P"
)
if not defined ISCC (
    echo.
    echo    Nie znaleziono Inno Setup 6 - potrzebny do stworzenia instalatora.
    echo    Pobierz i zainstaluj: https://jrsoftware.org/isdl.php
    echo    Nastepnie uruchom ten skrypt jeszcze raz.
    exit /b 1
)

echo Kompiluje instalator...
"%ISCC%" /Qp /O"installer" packaging\AutoClicker.iss
if errorlevel 1 (
    echo    Kompilacja instalatora zakonczona blediem.
    exit /b 1
)
echo.
echo    Gotowe: %CD%\installer\AutoClicker-Setup-1.0.0.exe
