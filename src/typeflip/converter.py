"""Text conversion engine with Persian ↔ English keyboard mapping and detection."""

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


class TextConverter:
    """Converts text between English and Persian keyboard layouts."""

    NORMALIZE_MAP = {
        "ي": "ی", "ك": "ک",
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ة": "ه", "ؤ": "و", "ئ": "ی",
        "ء": "", "َ": "", "ُ": "", "ِ": "",
        "ّ": "", "ً": "", "ٌ": "", "ٍ": "", "ْ": "",
    }

    @staticmethod
    def has_persian(text: str) -> bool:
        """Check if text contains any Persian Unicode characters."""
        return any("\u0600" <= c <= "\u06FF" or c == "‍" for c in text)

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize Arabic characters to their Persian equivalents."""
        for old, new in TextConverter.NORMALIZE_MAP.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def detect(text: str) -> str:
        """Detect the language direction: 'fa' for Persian, 'en' for English."""
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
        """Convert text between English and Persian based on detected language."""
        if not text:
            return text
        text = TextConverter.normalize(text)
        if not text.strip():
            return text
        mapping = FA_TO_EN if TextConverter.detect(text) == "fa" else EN_TO_FA
        return "".join(mapping.get(c, c) for c in text)

    @staticmethod
    def detect_display(text: str) -> str:
        """Return a human-readable string showing detected language direction."""
        if not text or not text.strip():
            return "—"
        lang = TextConverter.detect(text)
        if lang == "fa":
            return "🔤 Persian → English"
        return "🔤 English → Persian"