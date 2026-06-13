import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import winreg

logger = logging.getLogger(__name__)

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


@dataclass(frozen=True)
class StartupCommand:
    command: str


class WindowsStartupManager:
    def __init__(self, app_name: str, executable_resolver=None):
        self.app_name = app_name
        self._executable_resolver = executable_resolver or self._default_executable_resolver

    def _default_executable_resolver(self) -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        script_path = Path(sys.argv[0]).resolve()
        python_exe = Path(sys.executable).resolve()
        return f'"{python_exe}" "{script_path}"'

    def _open_run_key(self, access):
        return winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, access)

    def get_command(self) -> str | None:
        try:
            with self._open_run_key(winreg.KEY_READ) as key_handle:
                value, _ = winreg.QueryValueEx(key_handle, self.app_name)
                return value
        except FileNotFoundError:
            return None
        except OSError as exc:
            logger.error("Failed to read startup entry: %s", exc)
            return None

    def is_enabled(self) -> bool:
        return self.get_command() is not None

    def enable(self) -> bool:
        try:
            command = self._executable_resolver()
            with self._open_run_key(winreg.KEY_SET_VALUE) as key_handle:
                winreg.SetValueEx(key_handle, self.app_name, 0, winreg.REG_SZ, command)
            return self.get_command() == command
        except OSError as exc:
            logger.error("Failed to enable startup: %s", exc)
            return False

    def disable(self) -> bool:
        try:
            with self._open_run_key(winreg.KEY_SET_VALUE) as key_handle:
                winreg.DeleteValue(key_handle, self.app_name)
            return not self.is_enabled()
        except FileNotFoundError:
            return True
        except OSError as exc:
            logger.error("Failed to disable startup: %s", exc)
            return False
