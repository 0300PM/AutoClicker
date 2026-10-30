@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
title Budowanie AutoClicker.exe

echo [1/3] Sprawdzam Pythona...
set "PYCMD=python"
where py >nul 2>nul && set "PYCMD=py -3"
%PYCMD% -c "import tkinter, sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>nul
if errorlevel 1 (
    echo    Brak Pythona 3.9+ z Tkinter.
    echo    Zainstaluj Pythona ze strony https://www.python.org/downloads/
    echo    i zaznacz opcje "Add python.exe to PATH".
    exit /b 1
)

echo [2/3] Instaluje pynput i PyInstaller...
%PYCMD% -m pip install --disable-pip-version-check -q --upgrade pynput pyinstaller
if errorlevel 1 (
    echo    Nie udalo sie pobrac pakietow. Sprawdz internet i spróbuj ponownie.
    exit /b 1
)

echo [3/3] Buduje pojedynczy plik .exe...
%PYCMD% -m PyInstaller --noconfirm --clean packaging\AutoClicker.spec
if errorlevel 1 (
    echo    Budowanie przerwane bledem.
    exit /b 1
)

echo.
if exist "dist\AutoClicker.exe" (
    echo    Gotowe: %CD%\dist\AutoClicker.exe
) else (
    echo    Blad: nie powstal plik dist\AutoClicker.exe
    exit /b 1
)
