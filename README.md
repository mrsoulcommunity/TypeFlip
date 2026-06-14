# TypeFlip

<img src="assets/icon.png" alt="TypeFlip Icon" width="64" align="right">

TypeFlip is a lightweight Windows tool for **converting English ↔ Persian text** with one hotkey press.  
Works in any application — select text, press `F12` (or your custom hotkey), and the selected text is automatically converted.

## ✨ Features

| Feature | Description |
|---|---|
| 🌍 **Global Hotkey** | Select text anywhere and press `F12` to convert instantly |
| 🔄 **Bi-directional** | Automatically detects Persian or English text |
| 🎨 **Modern Dark UI** | Catppuccin-inspired dark theme — easy on the eyes |
| 👁️ **Live Preview** | Type in the app to see conversion in real-time |
| 🔍 **Language Detection** | Shows detected direction (Persian→English / English→Persian) |
| 🔢 **Character Count** | Live character counter while typing |
| 🖥️ **System Tray** | Minimizes to tray, stays out of your way |
| ⌨️ **Custom Hotkey** | Change the hotkey to any key combination |
| ⚡ **Auto-start** | Option to run at Windows startup |
| 📋 **Copy to Clipboard** | One-click copy from the result box |
| 🎯 **Ctrl+Enter** | Keyboard shortcut to convert in preview box |

## ⌨️ Shortcuts

| Shortcut | Action |
|----------|--------|
| `F12` (customizable) | Convert selected text in any window |
| `Ctrl+Enter` | Convert text in the preview box |

## 🚀 Quick Start

Run `run.bat` to install dependencies and launch the app.

## 📦 Build Executable

Run `build.bat` to build a standalone `TypeFlip.exe`.

## 📁 Project Structure

```
├── src/
│   ├── main.py                  # Entry point
│   └── typeflip/
│       ├── main.py              # Core app, converter, UI
│       ├── startup.py           # Windows auto-start manager
│       └── __init__.py
├── config/
│   └── typeflip.json            # Settings
├── assets/
│   ├── icon.ico                 # App icon (Windows)
│   └── icon.png                 # App icon (PNG)
├── logs/
│   └── typeflip.log             # Application logs
├── requirements.txt
├── run.bat
└── build.bat
```

## 🔮 Future Ideas

Here are features that could be added in future versions:

| Feature | Description | Priority |
|---|---|---|
| 🔤 **Persian Standard Keyboard** | Add support for the standard Persian keyboard layout (ISIRI 9147) alongside the current custom layout | Medium |
| 📝 **Auto-copy Result** | Option to automatically copy the converted result to clipboard | Low |
| 🎵 **Sound Feedback** | Play a subtle sound effect when conversion completes | Low |
| 📊 **Conversion History** | Show a log/history of recent conversions inside the UI | Medium |
| 🖼️ **Custom Themes** | Let users choose between light/dark themes or custom accent colors | Low |
| 🔑 **Advanced Hotkeys** | Support for multi-key hotkeys (Ctrl+Shift+F, etc.) | Medium |
| 🌐 **More Languages** | Add support for Arabic, Russian, or other keyboard layouts | High |
| 📱 **Portable Mode** | Save settings alongside the executable for USB drives | Low |
| 🧹 **Smart Detection** | Improve detection for mixed English/Persian text (e.g., code comments) | Medium |
| 🔄 **Toggle Direction** | Manual override for conversion direction (force En→Fa or Fa→En) | High |
| 🧪 **Auto-Update** | Check for updates and install newer versions automatically | Low |
| 📋 **Multiple Clipboard** | Store last N converted texts for quick access | Low |
| ⚙️ **Advanced Settings** | Adjust sleep timings, debounce delay, and other performance options | Low |
| 🖼️ **Window Snapping** | Remember window position and size between launches | Low |
| 🔔 **Notification on Convert** | Show a brief toast notification when hotkey conversion completes | Medium |

## 📜 Version History

- **1.4.0** — Dark mode UI, app icon, live language detection, character count, improved Persian keyboard mappings
- **1.3.1** — Initial release