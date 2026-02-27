# Configuration

## max_repeat

Unbounded quantifiers (`*`, `+`, `{n,}`) are capped at a maximum number of repetitions. The default is **100**.

You can set it per-instance:

```python
from string_gen import StringGen

gen = StringGen(r'\w+', max_repeat=10)
gen.render()  # 1-10 characters instead of 1-100
```

## Custom Alphabets

By default, character categories (`\w`, `.`, `[^...]`) generate ASCII characters. Use the `alphabet` parameter to generate strings from other scripts:

```python
from string_gen import StringGen
from string_gen.alphabets import CYRILLIC, ASCII

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

See [Alphabet Presets](../reference/alphabets.md) for all 22 available presets.

## configure()

Configure global defaults for all new `StringGen` instances. Per-instance values in the constructor take priority.

```python
import string_gen

# Set global max_repeat
string_gen.configure(max_repeat=20)

gen = StringGen(r'\w+')
gen.render()  # 1-20 characters

# Set global alphabet
string_gen.configure(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
```

Both parameters can be set at once:

```python
string_gen.configure(max_repeat=20, alphabet="αβγδε")
```

## reset()

Reset all global settings (`max_repeat` and `alphabet`) to their defaults:

```python
import string_gen

string_gen.configure(max_repeat=10, alphabet="αβγδε")
string_gen.reset()  # back to max_repeat=100, alphabet=None (ASCII)
```

## seed()

Re-seed the internal random number generator for reproducible output:

```python
gen = StringGen(r'\d{3}')
gen.seed(42)
gen.render()  # always the same result for the same seed
```

Seed can be set in the constructor too:

```python
gen = StringGen(r'\d{3}', seed=42)
```

Accepted seed types: `int`, `float`, `str`, `bytes`, `bytearray`, or `None`.

## Priority

Settings are resolved in this order (highest priority first):

1. **Constructor parameter** — `StringGen(r'\w+', max_repeat=5)`
2. **Global configure()** — `string_gen.configure(max_repeat=20)`
3. **Default** — `max_repeat=100`, `alphabet=None` (ASCII)

```python
import string_gen
from string_gen import StringGen

# Default: max_repeat=100
gen = StringGen(r'\w+')

# Global override: max_repeat=20
string_gen.configure(max_repeat=20)
gen = StringGen(r'\w+')  # uses 20

# Constructor override: max_repeat=5
gen = StringGen(r'\w+', max_repeat=5)  # uses 5
```
