import sys
import os
import json
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import win32clipboard
import win32con
import winreg

# ====================== CONFIG ======================
APP_NAME = "TypeFlip"
VERSION = "1.3.1"
SETTINGS_FILE = "TypeFlip.json"
LOG_FILE = "TypeFlip.log"

# ====================== LOGGING ======================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# ====================== KEYBOARD MAPPING ======================
EN_TO_FA = {
    '`': '‍', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹', '0': '۰',
    'q': 'ض', 'w': 'ص', 'e': 'ث', 'r': 'ق', 't': 'ف', 'y': 'غ', 'u': 'ع', 'i': 'ه', 'o': 'خ', 'p': 'ح',
    'a': 'ش', 's': 'س', 'd': 'ی', 'f': 'ب', 'g': 'ل', 'h': 'ا', 'j': 'ت', 'k': 'ن', 'l': 'م',
    'z': 'ظ', 'x': 'ط', 'c': 'ز', 'v': 'ر', 'b': 'ذ', 'n': 'د', 'm': 'پ',
    ',': 'و', '.': '.', '/': '/', ';': 'ک', "'": 'گ', '[': 'ج', ']': 'چ', '\\': '\\',
    '-': 'ـ', '=': '=', ' ': ' ',
}

FA_TO_EN = {v: k for k, v in EN_TO_FA.items()}
FA_TO_EN.update({
    'ی': 'd', 'ک': ';', 'گ': "'", 'چ': ']', 'ج': '[', '،': ',', '؟': '?', '؛': ';',
    '«': '{', '»': '}', 'ـ': '-', 'ؤ': 'A', 'ئ': 'S', 'ء': '}',
})

# ====================== CLIPBOARD MANAGER ======================
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
            except:
                time.sleep(0.015)
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except:
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
            except:
                time.sleep(0.015)
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except:
                    pass
        return False

# ====================== CONVERTER ======================
class TextConverter:
    @staticmethod
    def normalize(text: str) -> str:
        norm = {'ي': 'ی', 'ك': 'ک', 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ة': 'ه'}
        for old, new in norm.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def detect(text: str) -> str:
        fa = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        return "fa" if fa > len(text) * 0.35 else "en"

    @staticmethod
    def convert(text: str) -> str:
        if not text or not text.strip():
            return text
        text = TextConverter.normalize(text)
        mapping = FA_TO_EN if TextConverter.detect(text) == "fa" else EN_TO_FA
        return ''.join(mapping.get(c, c) for c in text)


# ====================== MAIN CONTROLLER ======================
class TypeFlip:
    def __init__(self, status_callback=None, log_callback=None):
        self.enabled = True
        self.last_trigger = 0.0
        self.debounce_time = 0.35
        self.settings = self.load_settings()
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.hotkey = self.settings.get("hotkey", "f12")
        self.enabled = bool(self.settings.get("enabled", True))

        self.setup_hotkey()
        logger.info(f"TypeFlip v{VERSION} started in silent mode")
        self.notify_status()

    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
        return {"hotkey": "f12", "enabled": True}

    def save_settings(self):
        data = {
            "hotkey": self.hotkey,
            "enabled": self.enabled,
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def notify_status(self, message=None):
        if self.status_callback:
            state = "Enabled" if self.enabled else "Disabled"
            text = message or f"{state} · Hotkey {self.hotkey.upper()}"
            self.status_callback(text)

    def notify_log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def setup_hotkey(self):
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.hotkey, self.trigger_conversion, suppress=False)
            logger.info(f"Global hotkey {self.hotkey.upper()} registered successfully")
        except Exception as e:
            logger.error(f"Hotkey registration failed: {e}")
            self.notify_status(f"Hotkey error: {e}")

    def set_hotkey(self, hotkey):
        hotkey = (hotkey or "").strip().lower()
        if not hotkey:
            raise ValueError("Hotkey cannot be empty")
        self.hotkey = hotkey
        self.setup_hotkey()
        self.save_settings()
        self.notify_status()

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.save_settings()
        self.notify_status()

    def trigger_conversion(self):
        now = time.time()
        if now - self.last_trigger < self.debounce_time:
            return
        self.last_trigger = now

        if not self.enabled:
            return

        threading.Thread(target=self.perform_silent_conversion, daemon=True).start()

    def perform_silent_conversion(self):
        original_clipboard = ClipboardManager.get()

        try:
            # Select All
            keyboard.send('ctrl+a')
            time.sleep(0.045)

            # Copy
            keyboard.send('ctrl+c')
            time.sleep(0.085)

            text = ClipboardManager.get()

            if not text or not text.strip():
                ClipboardManager.set(original_clipboard)
                return

            # Convert & Paste
            converted = TextConverter.convert(text)
            if ClipboardManager.set(converted):
                time.sleep(0.055)
                keyboard.send('ctrl+v')
                time.sleep(0.045)

            # Restore original clipboard
            ClipboardManager.set(original_clipboard)

            logger.info(f"Converted {len(text)} characters successfully")
            self.notify_log(f"Converted {len(text)} characters")

        except Exception as e:
            logger.error(f"Conversion error: {e}")
            self.notify_log(f"Conversion error: {e}")
            try:
                ClipboardManager.set(original_clipboard)
            except:
                pass

    def convert_text(self, text):
        return TextConverter.convert(text)

    def shutdown(self):
        try:
            keyboard.unhook_all()
        except Exception:
            pass


class TypeFlipUI:
    def __init__(self, app):
        self.app = app
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} {VERSION}")
        self.root.minsize(640, 420)
        self.root.geometry("700x460")
        self.root.configure(bg="#f6f6f4")

        self.status_var = tk.StringVar(value="Ready")
        self.hotkey_var = tk.StringVar(value=self.app.hotkey)
        self.enabled_var = tk.BooleanVar(value=self.app.enabled)
        self.result_var = tk.StringVar()
        self.log_var = tk.StringVar(value="Ready")

        self.build_styles()
        self.build_layout()
        self.sync_ui_from_app()

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_styles(self):
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

    def build_layout(self):
        outer = ttk.Frame(self.root, style="Root.TFrame", padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Root.TFrame")
        header.pack(fill="x")

        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side="left", anchor="w")
        ttk.Label(header, textvariable=self.status_var, style="Status.TLabel").pack(side="right", anchor="e")

        ttk.Label(outer, text="Convert selected text with one hotkey.", style="Meta.TLabel").pack(anchor="w", pady=(4, 14))

        settings = ttk.Frame(outer, style="Root.TFrame")
        settings.pack(fill="x")

        ttk.Checkbutton(
            settings,
            text="Enabled",
            variable=self.enabled_var,
            command=self.apply_enabled_state,
        ).pack(side="left")

        ttk.Label(settings, text="Hotkey", style="Line.TLabel").pack(side="left", padx=(16, 8))
        hotkey_entry = ttk.Entry(settings, textvariable=self.hotkey_var, width=10)
        hotkey_entry.pack(side="left")
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

    def sync_ui_from_app(self):
        self.refresh_status()

    def refresh_status(self):
        state = "Enabled" if self.enabled_var.get() else "Disabled"
        self.status_var.set(f"{state} · Hotkey {self.hotkey_var.get().strip().upper()}")

    def set_status(self, text):
        self.status_var.set(text)

    def push_log(self, text):
        self.log_var.set(text)

    def _set_result_text(self, text):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.configure(state="disabled")

    def apply_hotkey(self):
        try:
            self.app.set_hotkey(self.hotkey_var.get())
            self.refresh_status()
            self.push_log(f"Hotkey set to {self.app.hotkey.upper()}")
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e), parent=self.root)

    def apply_enabled_state(self):
        self.app.set_enabled(self.enabled_var.get())
        self.refresh_status()
        self.push_log("Service enabled" if self.enabled_var.get() else "Service disabled")

    def run_preview_conversion(self):
        text = self.source_box.get("1.0", "end-1c")
        converted = self.app.convert_text(text)
        self._set_result_text(converted)
        self.push_log("Converted")

    def clear_preview(self):
        self.source_box.delete("1.0", "end")
        self._set_result_text("")
        self.push_log("Cleared")

    def copy_result(self):
        result = self.result_box.get("1.0", "end-1c")
        if not result:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(result)
        self.push_log("Copied")

    def add_startup(self):
        try:
            add_to_startup()
            self.push_log("Startup set")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Failed to add to startup: {e}", parent=self.root)

    def close(self):
        self.app.shutdown()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ====================== STARTUP ======================
def add_to_startup():
    try:
        exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        logger.info("Successfully added to Windows startup")
    except Exception as e:
        logger.error(f"Failed to add to startup: {e}")


# ====================== MAIN ======================
if __name__ == "__main__":
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