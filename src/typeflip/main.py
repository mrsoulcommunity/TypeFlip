"""TypeFlip — Modern UI (2025). Frameless, dark, smooth, professional."""

import logging
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

import pystray
from PIL import Image, ImageDraw, ImageTk

from .config import (
    APP_NAME, VERSION,
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BG_HOVER, BG_INPUT,
    BORDER_SUBTLE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT, ACCENT_HOVER, GREEN, YELLOW, RED, MAUVE, SURFACE,
    FONT,
)
from .converter import TextConverter
from .engine import TypeFlipEngine
from .modern import TitleBar, GlassCard, AccentButton, SurfaceButton, ToggleSwitch, ModernTextArea

logger = logging.getLogger(__name__)

PLACEHOLDER = "Type or paste text here..."


class TypeFlipApp:
    """Main modern application window."""

    def __init__(self, engine: TypeFlipEngine):
        self.engine = engine

        # ── Root Window (frameless) ──
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} {VERSION}")
        self.root.overrideredirect(True)  # 🔥 Frameless!
        self.root.configure(bg=BG_PRIMARY)

        # Restore geometry
        s = engine.settings
        w = s.get("window_width", 640)
        h = s.get("window_height", 480)
        x = s.get("window_x")
        y = s.get("window_y")
        self.root.geometry(f"{w}x{h}+{x or 400}+{y or 200}")
        self.root.minsize(480, 360)

        if engine.always_on_top:
            self.root.attributes("-topmost", True)

        # ── Window icon ──
        self._set_icon()

        # ── State ──
        self.hotkey_var = tk.StringVar(value=engine.hotkey)
        self.enabled_var = tk.BooleanVar(value=engine.enabled)
        self.startup_var = tk.BooleanVar(value=engine.startup_enabled)
        self.top_var = tk.BooleanVar(value=engine.always_on_top)
        self.autocopy_var = tk.BooleanVar(value=engine.auto_copy)
        self.log_var = tk.StringVar(value="Ready")
        self.lang_var = tk.StringVar(value="—")
        self.count_var = tk.StringVar(value="0")

        self.tray_icon = None
        self.tray_thread = None
        self.is_hiding = False
        self.is_exiting = False
        self._has_placeholder = True
        self._geom_timer = None

        # ── Build ──
        self._build()
        self._setup_tray()
        self._bind_events()
        self._refresh_status()

        logger.info(f"{APP_NAME} v{VERSION} — Modern UI ready")

    # ─────────────────────────────────────────────
    #  BUILD
    # ─────────────────────────────────────────────

    def _build(self):
        """Construct the entire modern UI."""
        # ── Custom Title Bar ──
        self.title_bar = TitleBar(
            self.root, f"{APP_NAME} v{VERSION}",
            on_close=self._close,
        )

        # ── Main Container ──
        main = tk.Frame(self.root, bg=BG_PRIMARY)
        main.pack(fill="both", expand=True, padx=16, pady=(8, 14))

        # ── Status Badge ──
        self.status_badge = tk.Label(
            main, text="", bg=BG_PRIMARY, fg=GREEN,
            font=(FONT, 8, "bold"), anchor="e",
        )
        self.status_badge.pack(fill="x", pady=(0, 10))

        # ── Settings Row ──
        settings = tk.Frame(main, bg=BG_PRIMARY)
        settings.pack(fill="x", pady=(0, 12))

        self._toggle_row(settings, "Enabled", self.enabled_var, self._toggle_enabled)
        self._toggle_row(settings, "Auto-run", self.startup_var, self._toggle_startup)
        self._toggle_row(settings, "Pin", self.top_var, self._toggle_top)
        self._toggle_row(settings, "Auto-copy", self.autocopy_var, self._toggle_autocopy)

        # ── Hotkey Row ──
        hotkey_row = tk.Frame(main, bg=BG_PRIMARY)
        hotkey_row.pack(fill="x", pady=(4, 14))

        tk.Label(hotkey_row, text="Hotkey", bg=BG_PRIMARY, fg=TEXT_MUTED,
                 font=(FONT, 9)).pack(side="left")

        self.hotkey_entry = tk.Entry(
            hotkey_row, textvariable=self.hotkey_var, width=10,
            bg=BG_INPUT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
            relief="flat", bd=0, font=(FONT, 9),
            highlightthickness=1.5, highlightbackground=BORDER_SUBTLE,
            highlightcolor=ACCENT,
        )
        self.hotkey_entry.pack(side="left", padx=(6, 0))

        AccentButton(hotkey_row, "Apply", self._apply_hotkey,
                     width=60, height=26).pack(side="left", padx=(6, 0))

        tk.Label(hotkey_row, text="F12, ctrl+shift+f, ...",
                 bg=BG_PRIMARY, fg=TEXT_MUTED,
                 font=(FONT, 8)).pack(side="left", padx=(8, 0))

        # ── Input ──
        input_header = tk.Frame(main, bg=BG_PRIMARY)
        input_header.pack(fill="x", pady=(0, 4))

        tk.Label(input_header, text="INPUT", bg=BG_PRIMARY, fg=TEXT_MUTED,
                 font=(FONT, 8, "bold")).pack(side="left")
        self.lang_label = tk.Label(input_header, textvariable=self.lang_var,
                                    bg=BG_PRIMARY, fg=MAUVE, font=(FONT, 8))
        self.lang_label.pack(side="right")

        self.source = ModernTextArea(main, height=4)
        self.source.pack(fill="x", pady=(0, 8))
        self._set_placeholder()

        # ── Actions ──
        actions = tk.Frame(main, bg=BG_PRIMARY)
        actions.pack(fill="x", pady=(0, 10))

        AccentButton(actions, "Convert", self._convert,
                     width=80, height=30).pack(side="left")
        tk.Label(actions, text="Ctrl+Enter", bg=BG_PRIMARY, fg=TEXT_MUTED,
                 font=(FONT, 8)).pack(side="left", padx=(8, 0))

        SurfaceButton(actions, "Clear", self._clear).pack(side="left", padx=(14, 0))
        SurfaceButton(actions, "Copy", self._copy).pack(side="left", padx=(4, 0))

        # Swap
        swap_frame = tk.Frame(actions, bg=BG_PRIMARY)
        swap_frame.pack(side="left", padx=(8, 0))
        tk.Label(swap_frame, text="⇄", bg=BG_PRIMARY, fg=TEXT_SECONDARY,
                 font=(FONT, 14), cursor="hand2").pack()
        swap_frame.bind("<Button-1>", lambda e: self._swap())
        tk.Label(swap_frame, text="Swap", bg=BG_PRIMARY, fg=TEXT_MUTED,
                 font=(FONT, 7)).pack()

        # Count
        self.count_label = tk.Label(actions, textvariable=self.count_var,
                                     bg=BG_PRIMARY, fg=YELLOW, font=(FONT, 8))
        self.count_label.pack(side="right")

        # ── Result ──
        result_header = tk.Frame(main, bg=BG_PRIMARY)
        result_header.pack(fill="x", pady=(0, 4))

        tk.Label(result_header, text="RESULT", bg=BG_PRIMARY, fg=TEXT_MUTED,
                 font=(FONT, 8, "bold")).pack(side="left")

        self.result = ModernTextArea(main, height=3, bg="#15151c", readonly=True)
        self.result.pack(fill="both", expand=True, pady=(0, 6))

        # ── Footer ──
        footer = tk.Frame(main, bg=BG_PRIMARY)
        footer.pack(fill="x")

        tk.Label(footer, textvariable=self.log_var, bg=BG_PRIMARY,
                 fg=TEXT_MUTED, font=(FONT, 8)).pack(side="left")

        # About
        about_btn = tk.Label(footer, text="About", bg=BG_PRIMARY, fg=TEXT_MUTED,
                              font=(FONT, 8), cursor="hand2")
        about_btn.pack(side="right")
        about_btn.bind("<Enter>", lambda e: about_btn.configure(fg=TEXT_PRIMARY))
        about_btn.bind("<Leave>", lambda e: about_btn.configure(fg=TEXT_MUTED))
        about_btn.bind("<Button-1>", lambda e: self._about())

        tk.Label(footer, text=f"v{VERSION}", bg=BG_PRIMARY, fg=TEXT_MUTED,
                 font=(FONT, 8)).pack(side="right", padx=(0, 8))

    # ─────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────

    def _toggle_row(self, parent, label, var, cmd):
        """A row with label + toggle switch."""
        row = tk.Frame(parent, bg=BG_PRIMARY)
        row.pack(side="left", padx=(0, 14))

        tk.Label(row, text=label, bg=BG_PRIMARY, fg=TEXT_SECONDARY,
                 font=(FONT, 9)).pack(side="left", padx=(0, 4))
        toggle = ToggleSwitch(row, var, cmd)
        toggle.pack(side="left")
        return row

    def _set_icon(self):
        icon_paths = [
            Path(__file__).resolve().parents[2] / "assets" / "icon.ico",
            Path(__file__).resolve().parents[2] / "assets" / "icon.png",
        ]
        for p in icon_paths:
            if p.exists():
                try:
                    img = Image.open(str(p))
                    self.root.iconphoto(True, ImageTk.PhotoImage(img))
                except:
                    try:
                        self.root.iconbitmap(default=str(p))
                    except:
                        pass
                break

    def _set_placeholder(self):
        if not self._has_placeholder:
            return
        self.source.delete("1.0", "end")
        self.source.insert("1.0", PLACEHOLDER)
        self.source.configure(fg=TEXT_MUTED)
        self._has_placeholder = True
        self.lang_var.set("—")
        self.count_var.set("0")

    def _get_text(self):
        return "" if self._has_placeholder else self.source.get("1.0", "end-1c")

    def _log(self, msg):
        self.log_var.set(msg)

    def _refresh_status(self):
        state = "ON" if self.enabled_var.get() else "OFF"
        color = GREEN if self.enabled_var.get() else RED
        hotkey = self.hotkey_var.get().strip().upper()
        self.status_badge.configure(text=f"{'●' if self.enabled_var.get() else '○'} {state}  ·  {hotkey}", fg=color)

    # ─────────────────────────────────────────────
    #  ACTIONS
    # ─────────────────────────────────────────────

    def _on_source_change(self, e=None):
        if self._has_placeholder:
            return
        text = self.source.get("1.0", "end-1c")
        self.lang_var.set(TextConverter.detect_display(text))
        self.count_var.set(str(len(text.strip())))

    def _on_focus_in(self, e=None):
        if self._has_placeholder:
            self.source.delete("1.0", "end")
            self.source.configure(fg=TEXT_PRIMARY)
            self._has_placeholder = False
            self.lang_var.set("—")
            self.count_var.set("0")

    def _on_focus_out(self, e=None):
        text = self.source.get("1.0", "end-1c")
        if not text.strip() or text == PLACEHOLDER:
            self._set_placeholder()

    def _toggle_enabled(self):
        self.engine.set_enabled(self.enabled_var.get())
        self._refresh_status()
        self._log("ON" if self.enabled_var.get() else "OFF")

    def _toggle_startup(self):
        if self.engine.set_startup_enabled(self.startup_var.get()):
            self.startup_var.set(self.engine.startup_enabled)
            self._log("Auto-run ON" if self.startup_var.get() else "Auto-run OFF")

    def _toggle_top(self):
        self.root.attributes("-topmost", self.top_var.get())
        self.engine.set_always_on_top(self.top_var.get())
        self._log("Pinned" if self.top_var.get() else "Unpinned")

    def _toggle_autocopy(self):
        self.engine.set_auto_copy(self.autocopy_var.get())
        self._log("Auto-copy ON" if self.autocopy_var.get() else "Auto-copy OFF")

    def _apply_hotkey(self):
        try:
            self.engine.set_hotkey(self.hotkey_var.get())
            self._refresh_status()
            self._log(f"Hotkey: {self.engine.hotkey.upper()}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def _convert(self):
        text = self._get_text()
        if not text.strip():
            self._log("Nothing to convert")
            return
        converted = self.engine.convert_text(text)
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("1.0", converted)
        self.result.configure(state="disabled")

        changed = sum(1 for a, b in zip(text, converted) if a != b) + abs(len(text) - len(converted))
        self._on_source_change()

        if self.autocopy_var.get():
            self.root.clipboard_clear()
            self.root.clipboard_append(converted)
            self._log(f"✅ {changed} chars • copied")
        else:
            self._log(f"✅ {changed} chars")

    def _clear(self):
        self.source.delete("1.0", "end")
        self.source.configure(fg=TEXT_PRIMARY)
        self._has_placeholder = False
        self._set_placeholder()
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.configure(state="disabled")
        self.lang_var.set("—")
        self.count_var.set("0")
        self._log("Cleared")

    def _copy(self):
        text = self.result.get("1.0", "end-1c")
        if not text:
            self._log("Nothing to copy")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._log("✅ Copied")

    def _swap(self):
        source = self._get_text()
        result = self.result.get("1.0", "end-1c")
        if not result.strip() and not source.strip():
            self._log("Nothing to swap")
            return
        if self._has_placeholder:
            self.source.delete("1.0", "end")
            self.source.configure(fg=TEXT_PRIMARY)
            self._has_placeholder = False
        self.source.delete("1.0", "end")
        self.source.insert("1.0", result)
        self.source.configure(fg=TEXT_PRIMARY)
        self._has_placeholder = False
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("1.0", source)
        self.result.configure(state="disabled")
        self._on_source_change()
        self._log("⇄ Swapped")

    def _about(self):
        d = tk.Toplevel(self.root)
        d.title("About")
        d.configure(bg=BG_PRIMARY)
        d.overrideredirect(True)
        d.resizable(False, False)
        d.transient(self.root)
        d.grab_set()

        self.root.update_idletasks()
        px, py = self.root.winfo_x(), self.root.winfo_y()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        dw, dh = 300, 280
        d.geometry(f"{dw}x{dh}+{px+(pw-dw)//2}+{py+(ph-dh)//2}")
        d.configure(highlightbackground=BORDER_SUBTLE, highlightthickness=1)

        TitleBar(d, "About TypeFlip", on_close=d.destroy)

        frame = tk.Frame(d, bg=BG_PRIMARY, padx=24, pady=16)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="🔄", bg=BG_PRIMARY, fg=ACCENT,
                 font=(FONT, 28)).pack(pady=(0, 6))
        tk.Label(frame, text=APP_NAME, bg=BG_PRIMARY, fg=TEXT_PRIMARY,
                 font=(FONT, 14, "bold")).pack()
        tk.Label(frame, text=f"v{VERSION}", bg=BG_PRIMARY, fg=TEXT_SECONDARY,
                 font=(FONT, 9)).pack(pady=(0, 8))

        tk.Frame(frame, bg=BORDER_SUBTLE, height=1).pack(fill="x", pady=4)

        tk.Label(frame, text="English ↔ Persian converter\nSelect → press hotkey → done!",
                 bg=BG_PRIMARY, fg=TEXT_SECONDARY, font=(FONT, 9),
                 justify="center").pack(pady=6)

        AccentButton(frame, "Close", d.destroy, width=80, height=28).pack(pady=(8, 0))
        d.bind("<Escape>", lambda e: d.destroy())

    def _close(self):
        """Minimize to tray."""
        self._save_geom()
        self.root.withdraw()
        self._log("In tray")

    def _save_geom(self):
        if self.is_exiting:
            return
        try:
            x, y = self.root.winfo_x(), self.root.winfo_y()
            w, h = self.root.winfo_width(), self.root.winfo_height()
            if w >= self.root.winfo_reqwidth() and h >= self.root.winfo_reqheight():
                self.engine.save_window_geometry(x, y, w, h)
        except:
            pass

    # ─────────────────────────────────────────────
    #  TRAY
    # ─────────────────────────────────────────────

    def _make_tray_img(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((6, 6, 58, 58), radius=12, fill="#0f0f13",
                            outline=ACCENT, width=3)
        d.rounded_rectangle((18, 18, 46, 46), radius=6, outline=TEXT_PRIMARY, width=2)
        d.rectangle((24, 24, 40, 30), fill=TEXT_PRIMARY)
        d.rectangle((30, 24, 34, 42), fill=TEXT_PRIMARY)
        return img

    def _setup_tray(self):
        if self.tray_icon:
            return
        enable_txt = "✓ Enabled" if self.engine.enabled else "○ Disabled"
        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda i, m: self._show(), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(enable_txt, lambda i, m: self._tray_toggle()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", lambda i, m: self._exit()),
        )
        self.tray_icon = pystray.Icon(APP_NAME, self._make_tray_img(), APP_NAME, menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def _tray_toggle(self):
        self.engine.set_enabled(not self.engine.enabled)
        self.enabled_var.set(self.engine.enabled)
        self._refresh_status()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        self.tray_icon = None
        self._setup_tray()

    def _show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _exit(self):
        self.is_exiting = True
        self._save_geom()
        self.engine.shutdown()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        self.root.destroy()

    # ─────────────────────────────────────────────
    #  EVENTS
    # ─────────────────────────────────────────────

    def _bind_events(self):
        self.source.bind("<KeyRelease>", self._on_source_change)
        self.source.bind("<FocusIn>", self._on_focus_in)
        self.source.bind("<FocusOut>", self._on_focus_out)
        self.root.bind("<Control-Return>", lambda e: self._convert())
        self.root.bind("<Control-KeyPress-l>", lambda e: self._clear())
        self.root.bind("<Control-KeyPress-q>", lambda e: self._exit())
        self.root.bind("<Control-Shift-KeyPress-S>", lambda e: self._swap())
        self.root.bind("<Configure>", self._on_configure)

    def _on_configure(self, e=None):
        if self.is_exiting:
            return
        if self._geom_timer:
            self.root.after_cancel(self._geom_timer)
        self._geom_timer = self.root.after(500, self._save_geom)

    def run(self):
        self.source.focus_set()
        self.root.mainloop()


# ── Entry Point ───────────────────────────────────────────

def main():
    import sys
    if "--startup" in sys.argv:
        from .startup import WindowsStartupManager
        WindowsStartupManager(APP_NAME).enable()

    from .logger import logger as app_logger
    app_logger.info(f"Starting {APP_NAME} v{VERSION}")

    engine = TypeFlipEngine()
    try:
        app = TypeFlipApp(engine)
        app.run()
    except KeyboardInterrupt:
        app_logger.info("Terminated")
    finally:
        engine.shutdown()