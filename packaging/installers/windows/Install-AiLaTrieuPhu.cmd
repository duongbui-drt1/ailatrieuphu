@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-AiLaTrieuPhu.ps1"
pause
