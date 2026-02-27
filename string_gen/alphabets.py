"""
Alphabet presets for non-ASCII string generation.

Each constant is a plain string of letters (no digits, no punctuation).
Combine presets with ``+`` to create mixed alphabets.
"""

import string
from typing import Final, Tuple


def _ranges(*ranges: Tuple[int, int]) -> str:
    """Build a string from multiple Unicode code-point ranges."""
    return "".join(chr(c) for start, end in ranges for c in range(start, end))


ASCII: Final[str] = string.ascii_letters
CYRILLIC: Final[str] = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
GREEK: Final[str] = "αβγδεζηθικλμνξοπρσςτυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
LATIN_EXTENDED: Final[str] = (
    string.ascii_letters + "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß" + "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
)
HIRAGANA: Final[str] = _ranges((0x3041, 0x3097))
KATAKANA: Final[str] = _ranges((0x30A1, 0x30FB))
CJK: Final[str] = _ranges((0x4E00, 0x9FFF + 1))
HANGUL: Final[str] = _ranges((0xAC00, 0xD7A4))
ARABIC: Final[str] = _ranges((0x0621, 0x064B))
DEVANAGARI: Final[str] = _ranges((0x0904, 0x0970))
THAI: Final[str] = _ranges((0x0E01, 0x0E3B))
HEBREW: Final[str] = _ranges((0x05D0, 0x05EB))
BENGALI: Final[str] = _ranges((0x0985, 0x09B0), (0x09B6, 0x09BA))
TAMIL: Final[str] = _ranges(
    (0x0B85, 0x0B8B),
    (0x0B8E, 0x0B91),
    (0x0B92, 0x0B96),
    (0x0B99, 0x0B9B),
    (0x0B9C, 0x0B9D),
    (0x0B9E, 0x0BA0),
    (0x0BA3, 0x0BA5),
    (0x0BA8, 0x0BAB),
    (0x0BAE, 0x0BBA),
)
TELUGU: Final[str] = _ranges((0x0C05, 0x0C3A))
GEORGIAN: Final[str] = _ranges((0x10A0, 0x10C6), (0x10D0, 0x10FB))
ARMENIAN: Final[str] = _ranges((0x0531, 0x0557), (0x0561, 0x0588))
ETHIOPIC: Final[str] = _ranges((0x1200, 0x1249))
MYANMAR: Final[str] = _ranges((0x1000, 0x102B))
SINHALA: Final[str] = _ranges((0x0D85, 0x0D97), (0x0D9A, 0x0DC7))
GUJARATI: Final[str] = _ranges(
    (0x0A85, 0x0A8E),
    (0x0A8F, 0x0A92),
    (0x0A93, 0x0AAA),
    (0x0AAB, 0x0AB1),
    (0x0AB2, 0x0AB4),
    (0x0AB5, 0x0ABA),
)
PUNJABI: Final[str] = _ranges(
    (0x0A05, 0x0A0B),
    (0x0A0F, 0x0A11),
    (0x0A13, 0x0A29),
    (0x0A2A, 0x0A31),
    (0x0A32, 0x0A34),
    (0x0A35, 0x0A37),
    (0x0A38, 0x0A3A),
)
