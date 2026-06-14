# TypeFlip

English ↔ Persian text converter for Windows. Select text, press a hotkey, done.

## Files

```
src/
  main.py              # Entry point
  typeflip/
    __init__.py         # Package exports
    config.py           # Colors & constants
    converter.py        # Text conversion logic
    clipboard.py        # Clipboard operations
    settings.py         # Save/load settings
    engine.py           # Hotkey + core engine
    modern.py           # Modern UI components
    main.py             # Main app window
    startup.py          # Windows auto-start
    logger.py           # Logging setup
config/typeflip.json    # Your settings
```

## Run

```
pip install -r requirements.txt
python typeflip.py
```

Or double-click `run.bat`.