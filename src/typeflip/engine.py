"""Core TypeFlip application engine: hotkey management, global conversion, settings coordination."""

import logging
import threading
import time

import keyboard

from .config import APP_NAME, VERSION
from .converter import TextConverter
from .clipboard import ClipboardManager
from .settings import SettingsManager
from .startup import WindowsStartupManager

logger = logging.getLogger(__name__)


class TypeFlipEngine:
    """Core application engine managing hotkeys, global conversion, and settings."""

    def __init__(self, status_callback=None, log_callback=None):
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.settings_mgr = SettingsManager()
        self.startup_manager = WindowsStartupManager(APP_NAME)

        # Load persisted settings
        self.settings = self.settings_mgr.load()
        self.hotkey = self.settings.get("hotkey", "f12")
        self.enabled = bool(self.settings.get("enabled", True))
        self.always_on_top = bool(self.settings.get("always_on_top", False))
        self.auto_copy = bool(self.settings.get("auto_copy", False))
        self.startup_enabled = self.startup_manager.is_enabled()

        self.last_trigger = 0.0
        self.debounce_time = 0.35
        self.hotkey_handle = None

        self.setup_hotkey()
        logger.info(f"TypeFlip v{VERSION} started")
        self._notify_status()

    # ── Settings Helpers ──────────────────────────────────

    def _persist(self):
        """Save current settings to disk."""
        self.settings_mgr.save({
            "hotkey": self.hotkey,
            "enabled": self.enabled,
            "startup_enabled": self.startup_enabled,
            "always_on_top": self.always_on_top,
            "auto_copy": self.auto_copy,
        })

    def save_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        """Save window position and size settings."""
        self.settings_mgr.set("window_x", x)
        self.settings_mgr.set("window_y", y)
        self.settings_mgr.set("window_width", width)
        self.settings_mgr.set("window_height", height)

    # ── Callbacks ─────────────────────────────────────────

    def _notify_status(self, message: str | None = None) -> None:
        if self.status_callback:
            state = "🟢 Enabled" if self.enabled else "🔴 Disabled"
            self.status_callback(message or f"{state} · {self.hotkey.upper()}")

    def _notify_log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)

    # ── Hotkey Management ─────────────────────────────────

    def setup_hotkey(self) -> None:
        """Register or re-register the global hotkey. Raises on failure."""
        if self.hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(self.hotkey_handle)
            except Exception:
                pass
        try:
            self.hotkey_handle = keyboard.add_hotkey(
                self.hotkey, self.trigger_conversion, suppress=False
            )
            logger.info(f"Global hotkey {self.hotkey.upper()} registered")
        except Exception as exc:
            self.hotkey_handle = None
            logger.error(f"Hotkey registration failed: {exc}")
            self._notify_status("⚠️ Hotkey error")
            raise

    def set_hotkey(self, hotkey: str) -> None:
        """Change the global hotkey. Only persists on successful registration."""
        hotkey = (hotkey or "").strip().lower()
        if not hotkey:
            raise ValueError("Hotkey cannot be empty")
        old_hotkey = self.hotkey
        old_handle = self.hotkey_handle
        self.hotkey = hotkey
        try:
            self.setup_hotkey()
            self._persist()
            self._notify_status()
        except Exception:
            self.hotkey = old_hotkey
            self.hotkey_handle = old_handle
            raise

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the global hotkey listener."""
        self.enabled = bool(enabled)
        self._persist()
        self._notify_status()

    def set_startup_enabled(self, enabled: bool) -> bool:
        """Enable or disable Windows auto-start. Returns True on success."""
        desired_state = bool(enabled)
        success = (
            self.startup_manager.enable()
            if desired_state
            else self.startup_manager.disable()
        )
        if success:
            self.startup_enabled = self.startup_manager.is_enabled()
            self._persist()
            self._notify_status()
            return True
        self._notify_log("⚠️ Failed to update Windows startup")
        return False

    def set_always_on_top(self, enabled: bool) -> None:
        """Set always-on-top preference."""
        self.always_on_top = bool(enabled)
        self._persist()
        self._notify_log("📌 Always on Top: " + ("ON" if self.always_on_top else "OFF"))

    def set_auto_copy(self, enabled: bool) -> None:
        """Set auto-copy preference."""
        self.auto_copy = bool(enabled)
        self._persist()
        self._notify_log("📋 Auto-copy: " + ("ON" if self.auto_copy else "OFF"))

    def reset_settings(self) -> dict:
        """Reset all settings to factory defaults."""
        defaults = self.settings_mgr.reset()
        self.hotkey = defaults["hotkey"]
        self.enabled = defaults["enabled"]
        self.startup_enabled = False
        self.always_on_top = defaults["always_on_top"]
        self.auto_copy = defaults["auto_copy"]
        return defaults

    # ── Global Conversion ─────────────────────────────────

    def trigger_conversion(self) -> None:
        """Called by the hotkey listener. Debounces and fires silent conversion."""
        now = time.time()
        if now - self.last_trigger < self.debounce_time:
            return
        self.last_trigger = now
        if not self.enabled:
            return
        threading.Thread(target=self._perform_silent_conversion, daemon=True).start()

    def _perform_silent_conversion(self) -> None:
        """Select-all, copy, convert, paste-back in the active window."""
        original_clipboard = ClipboardManager.get()
        try:
            keyboard.send("ctrl+a")
            time.sleep(0.050)
            keyboard.send("ctrl+c")
            time.sleep(0.090)

            text = ClipboardManager.get()
            if not text or not text.strip():
                ClipboardManager.set(original_clipboard)
                return

            converted = TextConverter.convert(text)
            if converted != text and ClipboardManager.set(converted):
                time.sleep(0.060)
                keyboard.send("ctrl+v")
                time.sleep(0.050)

            ClipboardManager.set(original_clipboard)
            logger.info(f"Converted {len(text)} characters")
            self._notify_log(f"✅ Converted {len(text)} characters")
        except Exception as exc:
            logger.error(f"Conversion error: {exc}")
            self._notify_log("❌ Conversion error")
            try:
                ClipboardManager.set(original_clipboard)
            except Exception:
                pass

    def convert_text(self, text: str) -> str:
        """Convert text using the TextConverter (for preview UI)."""
        return TextConverter.convert(text)

    # ── Shutdown ──────────────────────────────────────────

    def shutdown(self) -> None:
        """Clean up hotkey registration."""
        try:
            if self.hotkey_handle is not None:
                keyboard.remove_hotkey(self.hotkey_handle)
                self.hotkey_handle = None
        except Exception:
            pass