"""Colors, constants, paths."""

from pathlib import Path
import sys

APP_NAME = "TypeFlip"
VERSION = "1.5.0"

# ── Premium Dark Palette (Figma-inspired) ──
BG_PRIMARY   = "#0f0f13"
BG_SECONDARY = "#18181d"
BG_CARD      = "#1e1e25"
BG_HOVER     = "#282830"
BG_INPUT     = "#141418"
BORDER_SUBTLE = "#2a2a35"
BORDER_FOCUS = "#6c6cf0"
TEXT_PRIMARY  = "#ededef"
TEXT_SECONDARY = "#9d9da8"
TEXT_MUTED    = "#5c5c6e"
ACCENT        = "#6c6cf0"
ACCENT_HOVER  = "#8383f5"
ACCENT_GLOW   = "#6c6cf0"
GREEN         = "#4ade80"
YELLOW        = "#facc15"
RED           = "#f87171"
MAUVE         = "#a78bfa"
SURFACE       = "#1e1e25"

FONT = "Segoe UI"
FONT_MONO = "JetBrains Mono"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def runtime_root():
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else PROJECT_ROOT

def bundle_root():
    return Path(getattr(sys, "_MEIPASS", runtime_root())) if getattr(sys, "frozen", False) else PROJECT_ROOT

SETTINGS_FILE = runtime_root() / "config" / "typeflip.json"
LOG_FILE = runtime_root() / "logs" / "typeflip.log"
LEGACY_SETTINGS_FILE = PROJECT_ROOT / "TypeFlip.json"


def ensure_project_structure():
    for name in ("config", "logs", "assets", "build", "dist"):
        (PROJECT_ROOT / name).mkdir(parents=True, exist_ok=True)


def ensure_runtime_structure():
    for name in ("config", "logs"):
        (runtime_root() / name).mkdir(parents=True, exist_ok=True)


# Ensure config and logs directories exist
ensure_project_structure()
ensure_runtime_structure()

DEFAULT_SETTINGS = {
    "hotkey": "f12", "enabled": True, "startup_enabled": False,
    "always_on_top": False, "auto_copy": False,
    "window_x": None, "window_y": None, "window_width": 640, "window_height": 480,
}