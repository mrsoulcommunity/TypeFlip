"""TypeFlip — English ↔ Persian converter for Windows."""

from .config import APP_NAME, VERSION
from .converter import TextConverter
from .main import main, TypeFlipApp

__all__ = ["APP_NAME", "VERSION", "TextConverter", "TypeFlipApp", "main"]