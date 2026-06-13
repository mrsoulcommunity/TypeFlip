@echo off
setlocal enabledelayedexpansion

title TypeFlip Build

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

echo ==================================================
echo TypeFlip build started
echo Root: %ROOT%
echo Python: %PYTHON%
echo ==================================================
echo.

echo [1/5] Installing dependencies...
%PYTHON% -m pip install --upgrade pip
if errorlevel 1 goto :build_fail
%PYTHON% -m pip install -r "%ROOT%requirements.txt"
if errorlevel 1 goto :build_fail

echo.
echo [2/5] Cleaning previous build outputs...
if exist "%ROOT%build" rmdir /s /q "%ROOT%build"
if exist "%ROOT%dist" rmdir /s /q "%ROOT%dist"

echo.
echo [3/5] Detecting icon...
set "ICON_ARG="
if exist "%ROOT%assets\icon.ico" set "ICON_ARG=--icon "%ROOT%assets\icon.ico""

echo.
echo [4/5] Building executable...
%PYTHON% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name TypeFlip ^
  --paths "%ROOT%src" ^
  %ICON_ARG% ^
  --add-data "%ROOT%config;config" ^
  --add-data "%ROOT%assets;assets" ^
  --distpath "%ROOT%dist" ^
  --workpath "%ROOT%build" ^
  --specpath "%ROOT%build" ^
  "%ROOT%typeflip.py"
if errorlevel 1 goto :build_fail

echo.
echo [5/5] Build complete.
echo Output: %ROOT%dist\TypeFlip.exe
exit /b 0

:build_fail
echo.
echo [ERROR] Build failed. Review the output above.
exit /b 1