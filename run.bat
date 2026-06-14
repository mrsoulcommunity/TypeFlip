@echo off
title TypeFlip - Launcher
color 0a

:: Detect Python interpreter (try common virtual env names first)
set "PYTHON=python"
for %%e in (".venv\Scripts\python.exe" "venv\Scripts\python.exe" "env\Scripts\python.exe" ".env\Scripts\python.exe") do (
    if exist "%%~e" set "PYTHON=%%~e"
)

:: Check Python availability
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    rem Try py -3 launcher as fallback
    set "PYTHON=py -3"
    %PYTHON% --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] No Python 3 interpreter found.
        echo.
        echo Make sure Python is installed and available in PATH, or create a
        echo virtual environment with: python -m venv .venv
        pause
        exit /b 1
    )
)

echo Installing/updating required packages...
%PYTHON% -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Launching TypeFlip...
%PYTHON% src\main.py
if errorlevel 1 (
    echo.
    echo [ERROR] TypeFlip exited with an error (code: %errorlevel%).
    pause
    exit /b 1
)