"""Modern UI components: custom title bar, glass cards, animated buttons."""

import tkinter as tk
from .config import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BG_HOVER, BG_INPUT,
    BORDER_SUBTLE, BORDER_FOCUS, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, ACCENT, ACCENT_HOVER, RED, FONT,
)


class TitleBar(tk.Frame):
    """Custom frameless title bar with drag, minimize, close."""

    def __init__(self, parent, title, on_close, on_minimize=None):
        super().__init__(parent, bg=BG_SECONDARY, height=38, highlightthickness=0)
        self.parent = parent
        self.on_close = on_close
        self.on_minimize = on_minimize
        self._start_x = 0
        self._start_y = 0

        # Drag binding
        self.bind("<ButtonPress-1>", self._start_drag)
        self.bind("<B1-Motion>", self._do_drag)
        self.bind("<Double-Button-1>", lambda e: self._toggle_maximize())

        # Title text
        self.title_label = tk.Label(
            self, text=title, bg=BG_SECONDARY, fg=TEXT_SECONDARY,
            font=(FONT, 10), padx=14,
        )
        self.title_label.pack(side="left")
        self.title_label.bind("<ButtonPress-1>", self._start_drag)
        self.title_label.bind("<B1-Motion>", self._do_drag)

        # Window controls
        ctrl_frame = tk.Frame(self, bg=BG_SECONDARY)
        ctrl_frame.pack(side="right", padx=(0, 8))

        btn_s = {"relief": "flat", "bd": 0, "cursor": "hand2", "width": 2, "font": (FONT, 10)}

        self.min_btn = tk.Button(ctrl_frame, text="─", bg=BG_SECONDARY, fg=TEXT_MUTED,
                                 activebackground=BG_HOVER, activeforeground=TEXT_PRIMARY,
                                 command=self._minimize, **btn_s)
        self.min_btn.pack(side="left", padx=2)

        self.close_btn = tk.Button(ctrl_frame, text="✕", bg=BG_SECONDARY, fg=TEXT_MUTED,
                                   activebackground=RED, activeforeground="white",
                                   command=self._close, **btn_s)
        self.close_btn.pack(side="left", padx=2)

        # Hover glow
        for btn in (self.min_btn, self.close_btn):
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=BG_HOVER))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=BG_SECONDARY))

        self.pack(fill="x")

    def _start_drag(self, e):
        self._start_x = e.x_root - self.parent.winfo_x()
        self._start_y = e.y_root - self.parent.winfo_y()

    def _do_drag(self, e):
        self.parent.geometry(f"+{e.x_root - self._start_x}+{e.y_root - self._start_y}")

    def _toggle_maximize(self):
        state = self.parent.state()
        if state == "zoomed":
            self.parent.state("normal")
        else:
            self.parent.state("zoomed")

    def _minimize(self):
        self.parent.state("iconic")

    def _close(self):
        self.on_close()


class GlassCard(tk.Frame):
    """Card with subtle border and hover glow."""

    def __init__(self, parent, **kwargs):
        pad = kwargs.pop("pad", (16, 12))
        super().__init__(
            parent, bg=BG_CARD,
            highlightbackground=BORDER_SUBTLE, highlightthickness=1,
            padx=pad[0], pady=pad[1],
        )


class AccentButton(tk.Canvas):
    """Smooth modern button with rounded rect and hover animation."""

    def __init__(self, parent, text, command, width=100, height=32, accent=ACCENT):
        super().__init__(parent, width=width, height=height,
                         bg=BG_PRIMARY, highlightthickness=0)
        self.command = command
        self.accent = accent
        self._hover = False

        self._rect = self.create_rounded_rect(2, 2, width-2, height-2, r=6,
                                               fill=accent, outline="")
        self._text_id = self.create_text(width//2, height//2, text=text,
                                          fill="#0f0f13", font=(FONT, 9, "bold"))

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: command())
        self.bind("<ButtonRelease-1>", lambda e: self._refresh())

        self.configure(cursor="hand2")

    def create_rounded_rect(self, x1, y1, x2, y2, r=8, **kwargs):
        """Draw a rounded rectangle."""
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, e):
        self._hover = True
        self.itemconfig(self._rect, fill=self._lighten(self.accent, 0.9))

    def _on_leave(self, e):
        self._hover = False
        self._refresh()

    def _refresh(self):
        self.itemconfig(self._rect, fill=self.accent)

    @staticmethod
    def _lighten(hex_color, factor=0.85):
        """Lighten a hex color."""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r / factor))
        g = min(255, int(g / factor))
        b = min(255, int(b / factor))
        return f"#{r:02x}{g:02x}{b:02x}"


class SurfaceButton(tk.Frame):
    """Text button with hover fill effect."""

    def __init__(self, parent, text, command, font_size=9, padx=12, pady=5):
        super().__init__(parent, bg=BG_PRIMARY)
        self.label = tk.Label(
            self, text=text, bg=BG_PRIMARY, fg=TEXT_SECONDARY,
            font=(FONT, font_size), padx=padx, pady=pady, cursor="hand2",
        )
        self.label.pack()
        self.label.bind("<Enter>", lambda e: self.label.configure(bg=BG_HOVER, fg=TEXT_PRIMARY))
        self.label.bind("<Leave>", lambda e: self.label.configure(bg=BG_PRIMARY, fg=TEXT_SECONDARY))
        self.label.bind("<Button-1>", lambda e: command())


class ToggleSwitch(tk.Canvas):
    """Modern toggle switch (on/off)."""

    def __init__(self, parent, variable, command, label=""):
        super().__init__(parent, width=36, height=18, bg=BG_PRIMARY, highlightthickness=0)
        self.var = variable
        self.command = command
        self.label_text = label
        self._state = variable.get()

        self._bg_rect = self.create_rounded_rect(0, 0, 36, 18, r=9, fill=self._bg_color(), outline="")
        self._knob = self.create_oval(3, 3, 15, 15, fill="#5c5c6e", outline="")

        self.bind("<Button-1>", self._toggle)
        self.configure(cursor="hand2")

    def create_rounded_rect(self, x1, y1, x2, y2, r=8, **kwargs):
        points = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
                  x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
                  x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _bg_color(self):
        return ACCENT if self.var.get() else "#2a2a35"

    def _toggle(self, e=None):
        self.var.set(not self.var.get())
        self._state = self.var.get()
        self._animate()
        self.command()

    def _animate(self):
        bg = self._bg_color()
        knob_x = 19 if self._state else 3
        self.itemconfig(self._bg_rect, fill=bg)
        self.coords(self._knob, knob_x, 3, knob_x+12, 15)

    def refresh(self):
        self._state = self.var.get()
        self._animate()


class ModernTextArea(tk.Text):
    """Styled text area with focus glow."""

    def __init__(self, parent, height=5, bg=None, readonly=False):
        super().__init__(
            parent, height=height, wrap="word",
            relief="flat", borderwidth=0,
            highlightthickness=1.5,
            highlightbackground=BORDER_SUBTLE,
            highlightcolor=BORDER_FOCUS,
            font=(FONT, 10), bg=bg or BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            padx=14, pady=10, spacing1=2, spacing2=1,
            state="normal" if not readonly else "disabled",
        )