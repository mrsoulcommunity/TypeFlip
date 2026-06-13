@echo off
title TypeFlip - Launcher
color 0a

set "PYTHON=python"
if exist .venv\Scripts\python.exe set "PYTHON=.venv\Scripts\python.exe"

echo Installing required packages...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r requirements.txt

echo.
echo Launching TypeFlip...
%PYTHON% src\main.py
pause