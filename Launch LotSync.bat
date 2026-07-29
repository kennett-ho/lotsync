@echo off
REM Double-click entry point for tools\launch.ps1. See tools\README.md /
REM README.md's "Developer Quick Start" section for what this does.
REM
REM %~dp0 is this .bat file's own directory, so this works no matter what
REM the current directory is when it's double-clicked.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\launch.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo LotSync failed to start -- see the messages above.
    pause
)
