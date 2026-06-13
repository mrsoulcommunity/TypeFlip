# TypeFlip

Minimal Windows desktop text conversion utility.

## Structure

- `src/` - application code and entry point
- `assets/` - optional packaged assets such as icons
- `config/` - default and runtime JSON settings
- `build/` - PyInstaller work files and spec output
- `dist/` - final packaged executable
- `logs/` - runtime logs

## Build

Run `build.bat` on Windows to install dependencies, clean previous artifacts, and generate `dist\TypeFlip.exe`.