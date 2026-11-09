@echo off
title AI Agent Hub - Windows
cd /d "%~dp0"
echo Starting AI Agent Hub...
where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start pythonw app.py
) else (
    python app.py
)
exit
