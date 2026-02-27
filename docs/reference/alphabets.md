# Alphabet Presets

The `string_gen.alphabets` module provides alphabet presets for non-ASCII string generation.

## Usage

```python
from string_gen import StringGen
from string_gen.alphabets import CYRILLIC, GREEK, ASCII

# Cyrillic word characters
gen = StringGen(r'\w{10}', alphabet=CYRILLIC)
gen.render()  # e.g. 'ёЩкРблнЫйМ'

# Mixed alphabets (combine with +)
gen = StringGen(r'\w{10}', alphabet=CYRILLIC + ASCII)
gen.render()  # mix of Cyrillic and Latin letters

# Custom alphabet — any string of letters
gen = StringGen(r'\w{5}', alphabet='αβγδε')
gen.render()  # e.g. 'γα3δ_'
```

## Available Presets

| Preset | Description |
|--------|-------------|
| `ASCII` | `string.ascii_letters` (default) |
| `CYRILLIC` | Russian alphabet (а-я, А-Я, ё, Ё) |
| `GREEK` | Greek alphabet (α-ω, Α-Ω) |
| `LATIN_EXTENDED` | ASCII + accented Latin characters |
| `HIRAGANA` | Japanese Hiragana |
| `KATAKANA` | Japanese Katakana |
| `CJK` | CJK Unified Ideographs |
| `HANGUL` | Korean Hangul syllables |
| `ARABIC` | Arabic script |
| `DEVANAGARI` | Devanagari script (Hindi, Marathi, Nepali) |
| `THAI` | Thai script |
| `HEBREW` | Hebrew script |
| `BENGALI` | Bengali/Bangla script |
| `TAMIL` | Tamil script |
| `TELUGU` | Telugu script |
| `GEORGIAN` | Georgian script |
| `ARMENIAN` | Armenian script |
| `ETHIOPIC` | Ethiopic/Ge'ez script (Amharic) |
| `MYANMAR` | Myanmar/Burmese script |
| `SINHALA` | Sinhala script |
| `GUJARATI` | Gujarati script |
| `PUNJABI` | Punjabi/Gurmukhi script |

## How Alphabets Affect Categories

When `alphabet` is set, it replaces `string.ascii_letters` in character category resolution:

| Category | Behavior |
|----------|----------|
| `\w` | `alphabet + digits + "_"` |
| `\W` | everything in the printable set that is not in `\w` |
| `\d` | always `0-9` (unchanged) |
| `\D` | everything in the printable set that is not `0-9` |
| `\s` | always standard whitespace (unchanged) |
| `\S` | everything in the printable set that is not whitespace |
| `.` | any character from the printable set except `\n` |
| `[^...]` | negated class drawn from the printable set |

The **printable set** is derived from the alphabet: `alphabet + digits + "_" + punctuation + whitespace`.
