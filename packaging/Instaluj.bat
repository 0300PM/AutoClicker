@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Instalacja AutoClicker (bez .exe)

echo [1/4] Sprawdzam Pythona...
set "PYCMD=python"
where py >nul 2>nul && set "PYCMD=py -3"
%PYCMD% --version >nul 2>nul
if errorlevel 1 (
    echo    Nie znaleziono Pythona. Zainstaluj Python 3.9+ z https://www.python.org/downloads/
    echo    i zaznacz "Add python.exe to PATH".
    exit /b 1
)

echo [2/4] Tworze srodowisko .venv...
%PYCMD% -m venv .venv
if errorlevel 1 (
    echo    Nie udalo sie utworzyc .venv.
    exit /b 1
)

echo [3/4] Instaluje zaleznosci...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo    Nie udalo sie zainstalowac pynput.
    exit /b 1
)

echo [4/4] Tworze skrót na pulpicie...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Create-Shortcut.ps1"

echo.
echo    Gotowe. Uruchom "AutoClicker" z pulpitu albo:
echo        .venv\Scripts\pythonw.exe app.py
echo.
pause
