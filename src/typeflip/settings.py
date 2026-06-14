"""Settings persistence with JSON file management, legacy migration, and defaults."""

import json
import logging
from pathlib import Path

from .config import (
    DEFAULT_SETTINGS,
    SETTINGS_FILE,
    LEGACY_SETTINGS_FILE,
    bundle_root,
)

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manages loading, saving, and migrating application settings."""

    def __init__(self):
        self._data: dict = {}

    def load(self) -> dict:
        """Load settings from file, migrating legacy configs if needed."""
        try:
            if SETTINGS_FILE.exists():
                with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._data = {**DEFAULT_SETTINGS, **raw}
                return self._data

            if LEGACY_SETTINGS_FILE.exists():
                with LEGACY_SETTINGS_FILE.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._data = {**DEFAULT_SETTINGS, **raw}
                self.save(self._data)
                return self._data

            bundled_default = bundle_root() / "config" / "typeflip.json"
            if bundled_default.exists():
                with bundled_default.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._data = {**DEFAULT_SETTINGS, **raw}
                self.save(self._data)
                return self._data

        except Exception as exc:
            logger.error(f"Failed to load settings: {exc}")

        self._data = dict(DEFAULT_SETTINGS)
        return self._data

    def save(self, data: dict | None = None) -> None:
        """Save settings to the JSON settings file."""
        if data is not None:
            self._data = {**DEFAULT_SETTINGS, **data}
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default=None):
        """Get a specific setting value by key."""
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a specific setting value and persist."""
        self._data[key] = value
        self.save()

    def get_all(self) -> dict:
        """Get all current settings as a dict."""
        return dict(self._data)

    def reset(self) -> dict:
        """Reset all settings to defaults and persist."""
        self._data = dict(DEFAULT_SETTINGS)
        self.save()
        return self._data