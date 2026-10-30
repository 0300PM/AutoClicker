@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Odinstalowywanie AutoClicker

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Remove-Install.ps1"
echo.
pause
