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

from .startup import WindowsStartupManager

APP_NAME = "TypeFlip"
VERSION = "1.4.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_SETTINGS_FILE = PROJECT_ROOT / "TypeFlip.json"

# ── Color Palette (Catppuccin Mocha inspired) ─────────────
COLOR_BG = "#1e1e2e"
COLOR_SURFACE = "#2a2a3e"
COLOR_SURFACE2 = "#363650"
COLOR_OVERLAY = "#313244"
COLOR_TEXT = "#cdd6f4"
COLOR_SUBTEXT0 = "#a6adc8"
COLOR_SUBTEXT1 = "#bac2de"
COLOR_TEXT_DIM = "#6c7086"
COLOR_ACCENT = "#89b4fa"
COLOR_ACCENT_HOVER = "#74c7ec"
COLOR_GREEN = "#a6e3a1"
COLOR_YELLOW = "#f9e2af"
COLOR_RED = "#f38ba8"
COLOR_MAUVE = "#cba6f7"
COLOR_BORDER = "#45475a"
COLOR_INPUT_BG = "#313244"
COLOR_FOCUS = "#89b4fa"


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

# ── Keyboard mapping ──────────────────────────────────────

EN_TO_FA = {
    # Numbers row
    "`": "‍", "1": "۱", "2": "۲", "3": "۳", "4": "۴", "5": "۵",
    "6": "۶", "7": "۷", "8": "۸", "9": "۹", "0": "۰",
    # Letters
    "q": "ض", "w": "ص", "e": "ث", "r": "ق", "t": "ف", "y": "غ",
    "u": "ع", "i": "ه", "o": "خ", "p": "ح",
    "a": "ش", "s": "س", "d": "ی", "f": "ب", "g": "ل", "h": "ا",
    "j": "ت", "k": "ن", "l": "م",
    "z": "ظ", "x": "ط", "c": "ز", "v": "ر", "b": "ذ", "n": "د", "m": "پ",
    # Symbols
    ",": "و", ".": ".", "/": "/", ";": "ک", "'": "گ",
    "[": "ج", "]": "چ", "\\": "\\",
    "-": "ـ", "=": "=", " ": " ",
    # Shift + letters
    "Q": "ً", "W": "ٌ", "E": "ٍ", "R": "َ", "T": "ُ", "Y": "ِ",
    "U": "ّ", "I": "ٰ", "O": "°", "P": "ؤ",
    "A": "ّ", "S": "َ", "D": "ّ", "F": "ِ", "G": "ُ", "H": "ً",
    "J": "ٍ", "K": "ٌ", "L": "ة",
    "Z": "ژ", "X": "َ", "C": "ٍ", "V": "ُ", "B": "ِ", "N": "ّ", "M": "(",
    # Shift + symbols
    "~": "÷", "!": "!", "@": "٬", "#": "٫", "$": "﷼", "%": "٪",
    "^": "×", "&": "·", "*": "٭", "(": ")", ")": "(",
    "_": "ـ", "+": "=",
    "{": "»", "}": "«", "|": "¦",
    ":": ":", '"': "«",
    "<": ">", ">": "<", "?": "؟",
}

FA_TO_EN = {v: k for k, v in EN_TO_FA.items()}
FA_TO_EN.update({
    "ی": "d", "ک": ";", "گ": "'", "چ": "]", "ج": "[",
    "،": ",", "؟": "?", "؛": ";",
    "«": '"', "»": '"', "ـ": "-",
})


# ── TextConverter ─────────────────────────────────────────

class TextConverter:
    NORMALIZE_MAP = {
        "ي": "ی", "ك": "ک",
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ة": "ه", "ؤ": "و", "ئ": "ی",
        "ء": "", "َ": "", "ُ": "", "ِ": "",
        "ّ": "", "ً": "", "ٌ": "", "ٍ": "", "ْ": "",
    }

    @staticmethod
    def has_persian(text: str) -> bool:
        return any("\u0600" <= c <= "\u06FF" or c == "‍" for c in text)

    @staticmethod
    def normalize(text: str) -> str:
        for old, new in TextConverter.NORMALIZE_MAP.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def detect(text: str) -> str:
        if not text:
            return "en"
        text_clean = TextConverter.normalize(text)
        fa = sum(1 for c in text_clean if "\u0600" <= c <= "\u06FF" or c == "‍")
        en = sum(1 for c in text_clean if c.isascii() and c.isalpha())

        if en == 0 and fa > 0:
            return "fa"
        if fa == 0:
            return "en"
        if len(text_clean) <= 3:
            return "fa" if fa > 0 else "en"
        return "fa" if fa >= en else "en"

    @staticmethod
    def convert(text: str) -> str:
        if not text:
            return text
        text = TextConverter.normalize(text)
        if not text.strip():
            return text
        mapping = FA_TO_EN if TextConverter.detect(text) == "fa" else EN_TO_FA
        return "".join(mapping.get(c, c) for c in text)

    @staticmethod
    def detect_display(text: str) -> str:
        if not text or not text.strip():
            return "—"
        lang = TextConverter.detect(text)
        if lang == "fa":
            return "🔤 Persian → English"
        return "🔤 English → Persian"


# ── ClipboardManager ──────────────────────────────────────

class ClipboardManager:
    _lock = threading.Lock()

    @staticmethod
    def get() -> str:
        for attempt in range(10):
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
                    if attempt < 9:
                        time.sleep(0.015)
        return ""

    @staticmethod
    def set(text: str) -> bool:
        for attempt in range(10):
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
                    if attempt < 9:
                        time.sleep(0.015)
        return False


# ── TypeFlip Core ─────────────────────────────────────────

class TypeFlip:
    def __init__(self, status_callback=None, log_callback=None):
        self.enabled = True
        self.last_trigger = 0.0
        self.debounce_time = 0.35
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.startup_manager = WindowsStartupManager(APP_NAME)
        self.settings = self.load_settings()
        self.hotkey = self.settings.get("hotkey", "f12")
        self.enabled = bool(self.settings.get("enabled", True))
        self.startup_enabled = self.startup_manager.is_enabled()
        self.hotkey_handle = None

        self.setup_hotkey()
        logger.info(f"TypeFlip v{VERSION} started")
        self.notify_status()

    def default_settings(self) -> dict:
        return {"hotkey": "f12", "enabled": True, "startup_enabled": False}

    def load_settings(self) -> dict:
        try:
            if SETTINGS_FILE.exists():
                with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                    return json.load(f)
            if LEGACY_SETTINGS_FILE.exists():
                with LEGACY_SETTINGS_FILE.open("r", encoding="utf-8") as f:
                    return json.load(f)
            bundled_default = bundle_root() / "config" / "typeflip.json"
            if bundled_default.exists():
                with bundled_default.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                self._write_settings_file(data)
                return data
        except Exception as exc:
            logger.error(f"Failed to load settings: {exc}")
        return self.default_settings()

    def _write_settings_file(self, data: dict) -> None:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_settings(self) -> None:
        self._write_settings_file({
            "hotkey": self.hotkey,
            "enabled": self.enabled,
            "startup_enabled": self.startup_enabled,
        })

    def notify_status(self, message: str | None = None) -> None:
        if self.status_callback:
            state = "🟢 Enabled" if self.enabled else "🔴 Disabled"
            self.status_callback(message or f"{state} · {self.hotkey.upper()}")

    def notify_log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)

    def setup_hotkey(self) -> None:
        try:
            if self.hotkey_handle is not None:
                try:
                    keyboard.remove_hotkey(self.hotkey_handle)
                except Exception:
                    pass
            self.hotkey_handle = keyboard.add_hotkey(
                self.hotkey, self.trigger_conversion, suppress=False
            )
            logger.info(f"Global hotkey {self.hotkey.upper()} registered")
        except Exception as exc:
            logger.error(f"Hotkey registration failed: {exc}")
            self.notify_status(f"⚠️ Hotkey error")

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

    def set_startup_enabled(self, enabled: bool) -> bool:
        desired_state = bool(enabled)
        success = (
            self.startup_manager.enable()
            if desired_state
            else self.startup_manager.disable()
        )
        if success:
            self.startup_enabled = self.startup_manager.is_enabled()
            self.save_settings()
            self.notify_status()
            return True
        self.notify_log("⚠️ Failed to update Windows startup")
        return False

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
            self.notify_log(f"✅ Converted {len(text)} characters")
        except Exception as exc:
            logger.error(f"Conversion error: {exc}")
            self.notify_log(f"❌ Conversion error")
            try:
                ClipboardManager.set(original_clipboard)
            except Exception:
                pass

    def convert_text(self, text: str) -> str:
        return TextConverter.convert(text)

    def shutdown(self) -> None:
        try:
            if self.hotkey_handle is not None:
                keyboard.remove_hotkey(self.hotkey_handle)
                self.hotkey_handle = None
        except Exception:
            pass


# ── UI ────────────────────────────────────────────────────

class TypeFlipUI:
    def __init__(self, app: TypeFlip):
        self.app = app
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} {VERSION}")
        self.root.minsize(620, 420)
        self.root.geometry("680x480+400+200")
        self.root.configure(bg=COLOR_BG)

        # Set window icon
        self._set_window_icon()

        self.status_var = tk.StringVar(value="Ready")
        self.hotkey_var = tk.StringVar(value=self.app.hotkey)
        self.enabled_var = tk.BooleanVar(value=self.app.enabled)
        self.startup_var = tk.BooleanVar(value=self.app.startup_enabled)
        self.log_var = tk.StringVar(value="Ready")
        self.lang_var = tk.StringVar(value="—")
        self.count_var = tk.StringVar(value="0 chars")
        self.tray_icon = None
        self.tray_thread = None
        self.is_hiding = False
        self.is_exiting = False

        self.build_styles()
        self.build_layout()
        self.setup_tray()
        self.refresh_status()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Control-Return>", lambda e: self.run_preview_conversion())
        self.source_box.bind("<Control-Return>", lambda e: self.run_preview_conversion())

    # ── Window Icon ───────────────────────────────────────

    def _set_window_icon(self) -> None:
        """Try to load the app icon from assets for the window title bar."""
        icon_paths = [
            runtime_root() / "assets" / "icon.ico",
            PROJECT_ROOT / "assets" / "icon.ico",
            PROJECT_ROOT / "assets" / "icon.png",
        ]
        for ipath in icon_paths:
            if ipath.exists():
                try:
                    img = Image.open(str(ipath))
                    self.root.iconphoto(True, tk.PhotoImage(file=str(ipath)))
                except Exception:
                    try:
                        self.root.iconbitmap(default=str(ipath))
                    except Exception:
                        pass
                break

    # ── Styles ────────────────────────────────────────────

    def build_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure("Root.TFrame", background=COLOR_BG)
        style.configure("Card.TFrame", background=COLOR_SURFACE, relief="flat")

        style.configure(
            "Title.TLabel", background=COLOR_BG, foreground=COLOR_TEXT,
            font=("Segoe UI", 16, "bold"),
        )
        style.configure(
            "Subtitle.TLabel", background=COLOR_BG, foreground=COLOR_SUBTEXT0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Meta.TLabel", background=COLOR_BG, foreground=COLOR_TEXT_DIM,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Section.TLabel", background=COLOR_BG, foreground=COLOR_SUBTEXT0,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Status.TLabel", background=COLOR_BG, foreground=COLOR_GREEN,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "StatusDisabled.TLabel", background=COLOR_BG, foreground=COLOR_RED,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Lang.TLabel", background=COLOR_BG, foreground=COLOR_MAUVE,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Count.TLabel", background=COLOR_BG, foreground=COLOR_YELLOW,
            font=("Segoe UI", 9),
        )

        # Accent button
        style.configure(
            "Accent.TButton", font=("Segoe UI", 10, "bold"),
            padding=(16, 8), background=COLOR_ACCENT, foreground=COLOR_BG,
            borderwidth=0, focuscolor=COLOR_ACCENT_HOVER,
        )
        style.map(
            "Accent.TButton",
            background=[("active", COLOR_ACCENT_HOVER), ("pressed", "#7aa2f7")],
        )

        # Flat button
        style.configure(
            "Flat.TButton", font=("Segoe UI", 10),
            padding=(12, 8), background=COLOR_SURFACE2, foreground=COLOR_TEXT,
            borderwidth=0,
        )
        style.map(
            "Flat.TButton",
            background=[("active", COLOR_BORDER), ("pressed", COLOR_SURFACE)],
        )

        # Entry
        style.configure(
            "TEntry", padding=(8, 6),
            fieldbackground=COLOR_INPUT_BG, foreground=COLOR_TEXT,
        )

        # Checkbutton
        style.configure(
            "TCheckbutton", background=COLOR_BG, foreground=COLOR_TEXT,
            font=("Segoe UI", 9),
        )
        style.map("TCheckbutton", foreground=[("selected", COLOR_ACCENT)])

        # Separator (use a Frame as a thin line)
        style.configure("TSeparator", background=COLOR_BORDER, relief="flat")

    # ── Layout ────────────────────────────────────────────

    def _make_entry_card(self, parent, height, bg=None):
        """Create a rounded-looking text area."""
        text = tk.Text(
            parent,
            height=height,
            wrap="word",
            relief="flat",
            borderwidth=0,
            highlightthickness=1.5,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_FOCUS,
            font=("Segoe UI", 10),
            bg=bg or COLOR_INPUT_BG,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            padx=12,
            pady=10,
            spacing1=2,
            spacing2=2,
        )
        return text

    def build_layout(self) -> None:
        outer = ttk.Frame(self.root, style="Root.TFrame", padding=20)
        outer.pack(fill="both", expand=True)

        # ── Header ──
        header = ttk.Frame(outer, style="Root.TFrame")
        header.pack(fill="x", pady=(0, 2))
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side="left", anchor="w")
        self.status_label = ttk.Label(
            header, textvariable=self.status_var, style="Status.TLabel",
        )
        self.status_label.pack(side="right", anchor="e")

        ttk.Label(
            outer, text="Select text anywhere and press your hotkey to instantly convert between English and Persian.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 16))

        # ── Settings Card ──
        settings_card = tk.Frame(outer, bg=COLOR_SURFACE, padx=14, pady=10)
        settings_card.pack(fill="x", pady=(0, 14))

        # Row 1: Options
        row1 = tk.Frame(settings_card, bg=COLOR_SURFACE)
        row1.pack(fill="x")

        self._tk_check(row1, "Enabled", self.enabled_var, self.apply_enabled_state)
        self._tk_check(row1, "Auto-start", self.startup_var, self.apply_startup_state)

        # Hotkey section
        tk.Label(row1, text="Hotkey:", bg=COLOR_SURFACE, fg=COLOR_SUBTEXT0,
                 font=("Segoe UI", 9)).pack(side="left", padx=(18, 6))
        hotkey_entry = tk.Entry(
            row1, textvariable=self.hotkey_var, width=10,
            bg=COLOR_INPUT_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT,
            relief="flat", bd=0, font=("Segoe UI", 9),
            highlightthickness=1, highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_FOCUS,
        )
        hotkey_entry.configure(
            highlightbackground=COLOR_BORDER, highlightcolor=COLOR_FOCUS
        )
        hotkey_entry.pack(side="left")

        apply_btn = tk.Button(
            row1, text="Apply", command=self.apply_hotkey,
            bg=COLOR_ACCENT, fg=COLOR_BG, activebackground=COLOR_ACCENT_HOVER,
            activeforeground=COLOR_BG, relief="flat", bd=0,
            font=("Segoe UI", 9, "bold"), padx=12, pady=4, cursor="hand2",
        )
        apply_btn.pack(side="left", padx=(8, 0))

        # ── Input Section ──
        input_header = tk.Frame(outer, bg=COLOR_BG)
        input_header.pack(fill="x")
        tk.Label(input_header, text="INPUT", bg=COLOR_BG, fg=COLOR_SUBTEXT0,
                 font=("Segoe UI", 9, "bold")).pack(side="left", anchor="w")
        self.lang_label = tk.Label(
            input_header, textvariable=self.lang_var,
            bg=COLOR_BG, fg=COLOR_MAUVE, font=("Segoe UI", 9),
        )
        self.lang_label.pack(side="right", anchor="e")

        self.source_box = self._make_entry_card(outer, height=6)
        self.source_box.pack(fill="both", expand=False, pady=(6, 10))

        # ── Actions Bar ──
        actions = tk.Frame(outer, bg=COLOR_BG)
        actions.pack(fill="x")

        convert_btn = tk.Button(
            actions, text="⚡ Convert", command=self.run_preview_conversion,
            bg=COLOR_ACCENT, fg=COLOR_BG, activebackground=COLOR_ACCENT_HOVER,
            activeforeground=COLOR_BG, relief="flat", bd=0,
            font=("Segoe UI", 10, "bold"), padx=18, pady=7, cursor="hand2",
        )
        convert_btn.pack(side="left")

        tk.Label(actions, text="Ctrl+Enter", bg=COLOR_BG, fg=COLOR_TEXT_DIM,
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 0))

        clear_btn = tk.Button(
            actions, text="✕ Clear", command=self.clear_preview,
            bg=COLOR_SURFACE2, fg=COLOR_TEXT, activebackground=COLOR_BORDER,
            activeforeground=COLOR_TEXT, relief="flat", bd=0,
            font=("Segoe UI", 9), padx=14, pady=7, cursor="hand2",
        )
        clear_btn.pack(side="left", padx=(14, 0))

        copy_btn = tk.Button(
            actions, text="📋 Copy", command=self.copy_result,
            bg=COLOR_SURFACE2, fg=COLOR_TEXT, activebackground=COLOR_BORDER,
            activeforeground=COLOR_TEXT, relief="flat", bd=0,
            font=("Segoe UI", 9), padx=14, pady=7, cursor="hand2",
        )
        copy_btn.pack(side="left", padx=(8, 0))

        self.count_label = tk.Label(
            actions, textvariable=self.count_var,
            bg=COLOR_BG, fg=COLOR_YELLOW, font=("Segoe UI", 9),
        )
        self.count_label.pack(side="right")

        # ── Separator ──
        sep = tk.Frame(outer, bg=COLOR_BORDER, height=1)
        sep.pack(fill="x", pady=14)

        # ── Result Section ──
        result_header = tk.Frame(outer, bg=COLOR_BG)
        result_header.pack(fill="x")
        tk.Label(result_header, text="RESULT", bg=COLOR_BG, fg=COLOR_SUBTEXT0,
                 font=("Segoe UI", 9, "bold")).pack(side="left", anchor="w")

        self.result_box = self._make_entry_card(outer, height=5, bg="#252538")
        self.result_box.pack(fill="both", expand=True, pady=(6, 0))

        # ── Footer ──
        footer = tk.Frame(outer, bg=COLOR_BG)
        footer.pack(fill="x", pady=(12, 0))
        tk.Label(footer, textvariable=self.log_var, bg=COLOR_BG,
                 fg=COLOR_TEXT_DIM, font=("Segoe UI", 9)).pack(side="left")
        tk.Label(footer, text=f"v{VERSION}", bg=COLOR_BG,
                 fg=COLOR_TEXT_DIM, font=("Segoe UI", 9)).pack(side="right")

        # Bind events
        self.source_box.bind("<KeyRelease>", self._on_source_change)

    def _tk_check(self, parent, text, variable, command):
        cb = tk.Checkbutton(
            parent, text=text, variable=variable, command=command,
            bg=COLOR_SURFACE, fg=COLOR_TEXT, selectcolor=COLOR_SURFACE2,
            activebackground=COLOR_SURFACE, activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9), relief="flat", bd=0,
            highlightthickness=0,
        )
        cb.pack(side="left")
        return cb

    # ── Events ────────────────────────────────────────────

    def _on_source_change(self, event=None) -> None:
        text = self.source_box.get("1.0", "end-1c")
        self.lang_var.set(TextConverter.detect_display(text))
        count = len(text.strip())
        self.count_var.set(f"{count} char{'s' if count != 1 else ''}")

    # ── Tray ──────────────────────────────────────────────

    def create_tray_image(self) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Background
        draw.rounded_rectangle((6, 6, 58, 58), radius=14, fill=COLOR_BG)
        draw.rounded_rectangle((6, 6, 58, 58), radius=14, outline=COLOR_ACCENT, width=3)
        # Inner border
        draw.rounded_rectangle((16, 16, 48, 48), radius=8, outline=COLOR_TEXT, width=3)
        # T letter
        draw.rectangle((20, 20, 44, 26), fill=COLOR_TEXT)
        draw.rectangle((30, 20, 34, 44), fill=COLOR_TEXT)
        return img

    def setup_tray(self) -> None:
        if self.tray_icon is not None:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Show / Restore", lambda icon, item: self.show_window(), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", lambda icon, item: self.exit_app()),
        )
        self.tray_icon = pystray.Icon(APP_NAME, self.create_tray_image(), APP_NAME, menu)
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
        self.push_log("Minimized to system tray")

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

    # ── Helpers ───────────────────────────────────────────

    def refresh_status(self) -> None:
        state = "Enabled" if self.enabled_var.get() else "Disabled"
        prefix = "🟢" if self.enabled_var.get() else "🔴"
        self.status_var.set(f"{prefix} {state} · {self.hotkey_var.get().strip().upper()}")
        style = "Status.TLabel" if self.enabled_var.get() else "StatusDisabled.TLabel"
        self.status_label.configure(style=style)

    def push_log(self, text: str) -> None:
        self.log_var.set(text)

    def _set_result_text(self, text: str) -> None:
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)

    # ── Actions ───────────────────────────────────────────

    def apply_hotkey(self) -> None:
        try:
            self.app.set_hotkey(self.hotkey_var.get())
            self.refresh_status()
            self.push_log(f"✅ Hotkey set to {self.app.hotkey.upper()}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self.root)

    def apply_enabled_state(self) -> None:
        self.app.set_enabled(self.enabled_var.get())
        self.refresh_status()
        self.push_log("🟢 Enabled" if self.enabled_var.get() else "🔴 Disabled")

    def apply_startup_state(self) -> None:
        if self.app.set_startup_enabled(self.startup_var.get()):
            self.startup_var.set(self.app.startup_enabled)
            self.push_log(
                "✅ Auto-start enabled" if self.startup_var.get() else "✅ Auto-start disabled"
            )
        else:
            self.startup_var.set(self.app.startup_enabled)
            messagebox.showerror(APP_NAME, "Could not update Windows startup.", parent=self.root)

    def run_preview_conversion(self) -> None:
        text = self.source_box.get("1.0", "end-1c")
        if not text.strip():
            self.push_log("Nothing to convert")
            return
        converted = self.app.convert_text(text)
        self._set_result_text(converted)

        # Count how many chars actually changed
        changed = sum(1 for a, b in zip(text, converted) if a != b)
        changed += abs(len(text) - len(converted))
        self.push_log(f"✅ Converted ({changed} chars changed)")
        self._on_source_change()

    def clear_preview(self) -> None:
        self.source_box.delete("1.0", "end")
        self._set_result_text("")
        self.lang_var.set("—")
        self.count_var.set("0 chars")
        self.push_log("Cleared")
        self.source_box.focus_set()

    def copy_result(self) -> None:
        result = self.result_box.get("1.0", "end-1c")
        if not result:
            self.push_log("Nothing to copy")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(result)
        self.push_log("✅ Copied to clipboard")

    def close(self) -> None:
        self.hide_window()

    def run(self) -> None:
        self.source_box.focus_set()
        self.root.mainloop()


def main() -> None:
    if "--startup" in sys.argv:
        startup_manager = WindowsStartupManager(APP_NAME)
        startup_manager.enable()

    app = TypeFlip()
    try:
        ui = TypeFlipUI(app)
        ui.run()
    except KeyboardInterrupt:
        logger.info("TypeFlip terminated")
    finally:
        app.shutdown()