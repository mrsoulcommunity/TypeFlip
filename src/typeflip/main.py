import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import keyboard
import pystray
from PIL import Image, ImageDraw
import win32clipboard
import win32con
import winreg

APP_NAME = "TypeFlip"
VERSION = "1.3.1"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_SETTINGS_FILE = PROJECT_ROOT / "TypeFlip.json"


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", runtime_root()))
    return PROJECT_ROOT


def ensure_project_structure() -> None:
    for folder_name in ("config", "logs", "assets", "build", "dist"):
        (PROJECT_ROOT / folder_name).mkdir(parents=True, exist_ok=True)


def ensure_runtime_structure() -> None:
    for folder_name in ("config", "logs"):
        (runtime_root() / folder_name).mkdir(parents=True, exist_ok=True)


ensure_project_structure()
ensure_runtime_structure()
LOG_FILE = runtime_root() / "logs" / "typeflip.log"
SETTINGS_FILE = runtime_root() / "config" / "typeflip.json"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)

EN_TO_FA = {
    "`": "‍", "1": "۱", "2": "۲", "3": "۳", "4": "۴", "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹", "0": "۰",
    "q": "ض", "w": "ص", "e": "ث", "r": "ق", "t": "ف", "y": "غ", "u": "ع", "i": "ه", "o": "خ", "p": "ح",
    "a": "ش", "s": "س", "d": "ی", "f": "ب", "g": "ل", "h": "ا", "j": "ت", "k": "ن", "l": "م",
    "z": "ظ", "x": "ط", "c": "ز", "v": "ر", "b": "ذ", "n": "د", "m": "پ",
    ",": "و", ".": ".", "/": "/", ";": "ک", "'": "گ", "[": "ج", "]": "چ", "\\": "\\",
    "-": "ـ", "=": "=", " ": " ",
}

FA_TO_EN = {v: k for k, v in EN_TO_FA.items()}
FA_TO_EN.update({
    "ی": "d", "ک": ";", "گ": "'", "چ": "]", "ج": "[", "،": ",", "؟": "?", "؛": ";",
    "«": "{", "»": "}", "ـ": "-", "ؤ": "A", "ئ": "S", "ء": "}",
})


class ClipboardManager:
    @staticmethod
    def get() -> str:
        for _ in range(10):
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                    return data or ""
                win32clipboard.CloseClipboard()
            except Exception:
                time.sleep(0.015)
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
        return ""

    @staticmethod
    def set(text: str) -> bool:
        for _ in range(10):
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                return True
            except Exception:
                time.sleep(0.015)
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
        return False


class TextConverter:
    @staticmethod
    def normalize(text: str) -> str:
        norm = {"ي": "ی", "ك": "ک", "أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه"}
        for old, new in norm.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def detect(text: str) -> str:
        fa = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
        return "fa" if fa > len(text) * 0.35 else "en"

    @staticmethod
    def convert(text: str) -> str:
        if not text or not text.strip():
            return text
        text = TextConverter.normalize(text)
        mapping = FA_TO_EN if TextConverter.detect(text) == "fa" else EN_TO_FA
        return "".join(mapping.get(c, c) for c in text)


class TypeFlip:
    def __init__(self, status_callback=None, log_callback=None):
        self.enabled = True
        self.last_trigger = 0.0
        self.debounce_time = 0.35
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.settings = self.load_settings()
        self.hotkey = self.settings.get("hotkey", "f12")
        self.enabled = bool(self.settings.get("enabled", True))

        self.setup_hotkey()
        logger.info(f"TypeFlip v{VERSION} started")
        self.notify_status()

    def default_settings(self) -> dict:
        return {"hotkey": "f12", "enabled": True}

    def load_settings(self) -> dict:
        try:
            if SETTINGS_FILE.exists():
                with SETTINGS_FILE.open("r", encoding="utf-8") as file_handle:
                    return json.load(file_handle)

            if LEGACY_SETTINGS_FILE.exists():
                with LEGACY_SETTINGS_FILE.open("r", encoding="utf-8") as file_handle:
                    return json.load(file_handle)

            bundled_default = bundle_root() / "config" / "typeflip.json"
            if bundled_default.exists():
                with bundled_default.open("r", encoding="utf-8") as file_handle:
                    data = json.load(file_handle)
                self._write_settings_file(data)
                return data
        except Exception as exc:
            logger.error(f"Failed to load settings: {exc}")
        return self.default_settings()

    def _write_settings_file(self, data: dict) -> None:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SETTINGS_FILE.open("w", encoding="utf-8") as file_handle:
            json.dump(data, file_handle, ensure_ascii=False, indent=2)

    def save_settings(self) -> None:
        self._write_settings_file({"hotkey": self.hotkey, "enabled": self.enabled})

    def notify_status(self, message: str | None = None) -> None:
        if self.status_callback:
            state = "Enabled" if self.enabled else "Disabled"
            self.status_callback(message or f"{state} · {self.hotkey.upper()}")

    def notify_log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)

    def setup_hotkey(self) -> None:
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.hotkey, self.trigger_conversion, suppress=False)
            logger.info(f"Global hotkey {self.hotkey.upper()} registered")
        except Exception as exc:
            logger.error(f"Hotkey registration failed: {exc}")
            self.notify_status(f"Hotkey error: {exc}")

    def set_hotkey(self, hotkey: str) -> None:
        hotkey = (hotkey or "").strip().lower()
        if not hotkey:
            raise ValueError("Hotkey cannot be empty")
        self.hotkey = hotkey
        self.setup_hotkey()
        self.save_settings()
        self.notify_status()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self.save_settings()
        self.notify_status()

    def trigger_conversion(self) -> None:
        now = time.time()
        if now - self.last_trigger < self.debounce_time:
            return
        self.last_trigger = now
        if not self.enabled:
            return
        threading.Thread(target=self.perform_silent_conversion, daemon=True).start()

    def perform_silent_conversion(self) -> None:
        original_clipboard = ClipboardManager.get()

        try:
            keyboard.send("ctrl+a")
            time.sleep(0.045)

            keyboard.send("ctrl+c")
            time.sleep(0.085)

            text = ClipboardManager.get()
            if not text or not text.strip():
                ClipboardManager.set(original_clipboard)
                return

            converted = TextConverter.convert(text)
            if ClipboardManager.set(converted):
                time.sleep(0.055)
                keyboard.send("ctrl+v")
                time.sleep(0.045)

            ClipboardManager.set(original_clipboard)
            logger.info(f"Converted {len(text)} characters successfully")
            self.notify_log(f"Converted {len(text)} characters")
        except Exception as exc:
            logger.error(f"Conversion error: {exc}")
            self.notify_log(f"Conversion error: {exc}")
            try:
                ClipboardManager.set(original_clipboard)
            except Exception:
                pass

    def convert_text(self, text: str) -> str:
        return TextConverter.convert(text)

    def shutdown(self) -> None:
        try:
            keyboard.unhook_all()
        except Exception:
            pass


class TypeFlipUI:
    def __init__(self, app: TypeFlip):
        self.app = app
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} {VERSION}")
        self.root.minsize(640, 420)
        self.root.geometry("700x460")
        self.root.configure(bg="#f6f6f4")

        self.status_var = tk.StringVar(value="Ready")
        self.hotkey_var = tk.StringVar(value=self.app.hotkey)
        self.enabled_var = tk.BooleanVar(value=self.app.enabled)
        self.log_var = tk.StringVar(value="Ready")
        self.tray_icon = None
        self.tray_thread = None
        self.is_hiding = False
        self.is_exiting = False

        self.build_styles()
        self.build_layout()
        self.setup_tray()
        self.refresh_status()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Root.TFrame", background="#f6f6f4")
        style.configure("Title.TLabel", background="#f6f6f4", foreground="#111111", font=("Segoe UI", 17, "bold"))
        style.configure("Meta.TLabel", background="#f6f6f4", foreground="#666666", font=("Segoe UI", 9))
        style.configure("Line.TLabel", background="#f6f6f4", foreground="#222222", font=("Segoe UI", 10))
        style.configure("Status.TLabel", background="#f6f6f4", foreground="#666666", font=("Segoe UI", 9))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 6))
        style.configure("Flat.TButton", font=("Segoe UI", 10), padding=(10, 6))
        style.configure("TEntry", padding=(6, 4))
        style.configure("TCheckbutton", background="#f6f6f4", foreground="#222222", font=("Segoe UI", 9))

    def build_layout(self) -> None:
        outer = ttk.Frame(self.root, style="Root.TFrame", padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Root.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side="left", anchor="w")
        ttk.Label(header, textvariable=self.status_var, style="Status.TLabel").pack(side="right", anchor="e")

        ttk.Label(outer, text="Convert selected text with one hotkey.", style="Meta.TLabel").pack(anchor="w", pady=(4, 14))

        settings = ttk.Frame(outer, style="Root.TFrame")
        settings.pack(fill="x")
        ttk.Checkbutton(settings, text="Enabled", variable=self.enabled_var, command=self.apply_enabled_state).pack(side="left")
        ttk.Label(settings, text="Hotkey", style="Line.TLabel").pack(side="left", padx=(16, 8))
        ttk.Entry(settings, textvariable=self.hotkey_var, width=10).pack(side="left")
        ttk.Button(settings, text="Apply", style="Flat.TButton", command=self.apply_hotkey).pack(side="left", padx=(8, 0))
        ttk.Button(settings, text="Startup", style="Flat.TButton", command=self.add_startup).pack(side="right")

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=14)

        ttk.Label(outer, text="Input", style="Line.TLabel").pack(anchor="w")
        self.source_box = tk.Text(
            outer,
            height=6,
            wrap="word",
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#d6d6d2",
            highlightcolor="#bcbcb7",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#111111",
            insertbackground="#111111",
        )
        self.source_box.pack(fill="both", expand=False, pady=(6, 12))

        actions = ttk.Frame(outer, style="Root.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="Convert", style="Accent.TButton", command=self.run_preview_conversion).pack(side="left")
        ttk.Button(actions, text="Clear", style="Flat.TButton", command=self.clear_preview).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Copy", style="Flat.TButton", command=self.copy_result).pack(side="left", padx=(8, 0))

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=14)

        ttk.Label(outer, text="Result", style="Line.TLabel").pack(anchor="w")
        self.result_box = tk.Text(
            outer,
            height=5,
            wrap="word",
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#ddddda",
            highlightcolor="#bcbcb7",
            font=("Segoe UI", 10),
            bg="#fbfbfa",
            fg="#111111",
            state="disabled",
        )
        self.result_box.pack(fill="both", expand=True, pady=(6, 0))

        footer = ttk.Frame(outer, style="Root.TFrame")
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, textvariable=self.log_var, style="Meta.TLabel").pack(side="left")
        ttk.Label(footer, text=f"v{VERSION}", style="Meta.TLabel").pack(side="right")

    def create_tray_image(self) -> Image.Image:
        image = Image.new("RGBA", (64, 64), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill="#111111")
        draw.rounded_rectangle((18, 18, 46, 46), radius=8, outline="#f6f6f4", width=3)
        draw.line((22, 32, 42, 32), fill="#f6f6f4", width=3)
        draw.line((32, 22, 32, 42), fill="#f6f6f4", width=3)
        return image

    def setup_tray(self) -> None:
        if self.tray_icon is not None:
            return

        menu = pystray.Menu(
            pystray.MenuItem("Show / Restore", lambda icon, item: self.show_window(), default=True),
            pystray.MenuItem("Exit", lambda icon, item: self.exit_app()),
        )
        self.tray_icon = pystray.Icon(
            APP_NAME,
            self.create_tray_image(),
            APP_NAME,
            menu,
        )
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def show_window(self) -> None:
        if self.is_exiting:
            return
        self.is_hiding = False
        self.root.after(0, self._show_window)

    def _show_window(self) -> None:
        if self.is_exiting:
            return
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def hide_window(self) -> None:
        if self.is_exiting or self.is_hiding:
            return
        self.is_hiding = True
        self.root.withdraw()
        self.push_log("Running in tray")

    def exit_app(self) -> None:
        if self.is_exiting:
            return
        self.is_exiting = True
        self.app.shutdown()
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.after(0, self.root.destroy)

    def refresh_status(self) -> None:
        state = "Enabled" if self.enabled_var.get() else "Disabled"
        self.status_var.set(f"{state} · {self.hotkey_var.get().strip().upper()}")

    def push_log(self, text: str) -> None:
        self.log_var.set(text)

    def _set_result_text(self, text: str) -> None:
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.configure(state="disabled")

    def apply_hotkey(self) -> None:
        try:
            self.app.set_hotkey(self.hotkey_var.get())
            self.refresh_status()
            self.push_log(f"Hotkey set to {self.app.hotkey.upper()}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self.root)

    def apply_enabled_state(self) -> None:
        self.app.set_enabled(self.enabled_var.get())
        self.refresh_status()
        self.push_log("Service enabled" if self.enabled_var.get() else "Service disabled")

    def run_preview_conversion(self) -> None:
        text = self.source_box.get("1.0", "end-1c")
        converted = self.app.convert_text(text)
        self._set_result_text(converted)
        self.push_log("Converted")

    def clear_preview(self) -> None:
        self.source_box.delete("1.0", "end")
        self._set_result_text("")
        self.push_log("Cleared")

    def copy_result(self) -> None:
        result = self.result_box.get("1.0", "end-1c")
        if not result:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(result)
        self.push_log("Copied")

    def add_startup(self) -> None:
        try:
            add_to_startup()
            self.push_log("Startup set")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Failed to add to startup: {exc}", parent=self.root)

    def close(self) -> None:
        self.hide_window()

    def run(self) -> None:
        self.root.mainloop()


def add_to_startup() -> None:
    try:
        executable_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
        registry_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(registry_key, APP_NAME, 0, winreg.REG_SZ, executable_path)
        winreg.CloseKey(registry_key)
        logger.info("Successfully added to Windows startup")
    except Exception as exc:
        logger.error(f"Failed to add to startup: {exc}")


def main() -> None:
    if "--startup" in sys.argv:
        add_to_startup()

    app = TypeFlip()
    try:
        ui = TypeFlipUI(app)
        ui.run()
    except KeyboardInterrupt:
        logger.info("TypeFlip terminated")
    finally:
        app.shutdown()
