@echo off
title TypeFlip - Launcher
color 0a

set "PYTHON=python"
if exist .venv\Scripts\python.exe set "PYTHON=.venv\Scripts\python.exe"

echo Installing required packages...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install keyboard pywin32

echo.
echo Launching TypeFlip...
%PYTHON% TypeFlip.py
pause