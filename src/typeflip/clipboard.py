"""Clipboard operations with thread-safe access and retry logic."""

import threading
import time

import win32clipboard
import win32con


class ClipboardManager:
    """Thread-safe Windows clipboard manager with automatic retry."""

    _lock = threading.Lock()
    _MAX_RETRIES = 10
    _RETRY_DELAY = 0.015

    @staticmethod
    def get() -> str:
        """Get text from the clipboard with retry logic."""
        for attempt in range(ClipboardManager._MAX_RETRIES):
            with ClipboardManager._lock:
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                            return data or ""
                        return ""
                    finally:
                        win32clipboard.CloseClipboard()
                except Exception:
                    if attempt < ClipboardManager._MAX_RETRIES - 1:
                        time.sleep(ClipboardManager._RETRY_DELAY)
        return ""

    @staticmethod
    def set(text: str) -> bool:
        """Set text to the clipboard with retry logic. Returns True on success."""
        for attempt in range(ClipboardManager._MAX_RETRIES):
            with ClipboardManager._lock:
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
                        return True
                    finally:
                        win32clipboard.CloseClipboard()
                except Exception:
                    if attempt < ClipboardManager._MAX_RETRIES - 1:
                        time.sleep(ClipboardManager._RETRY_DELAY)
        return False