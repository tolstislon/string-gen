# Getting Started

## Installation

=== "pip"

    ```bash
    pip install string-gen
    ```

=== "uv"

    ```bash
    uv add string-gen
    ```

=== "poetry"

    ```bash
    poetry add string-gen
    ```

## Basic Usage

Create a `StringGen` instance with a regex pattern, then call `render()` to produce a random matching string:

```python
from string_gen import StringGen

gen = StringGen(r'(A|B)\d{4}(\.|-)\d{1}')
print(gen.render())  # e.g. B9954.4
print(gen.render())  # e.g. A5292-1
```

Each call to `render()` produces a new random string matching the pattern.

## UUID-like Strings

Patterns can be as simple or complex as you need:

```python
gen = StringGen(r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}')
print(gen.render())  # e.g. 52aabe4b-01fa-4b33-8976-b53b09f49e72
```

Or use the built-in `UUID4` pattern:

```python
from string_gen.patterns import UUID4

gen = StringGen(UUID4)
print(gen.render())  # e.g. 52aabe4b-01fa-4b33-8976-b53b09f49e72
```

## Reproducible Output

Pass a `seed` to get the same sequence every time:

```python
gen = StringGen(r'\d{4}', seed=42)
print(gen.render())  # always the same result for seed=42
```

## Multiple Strings

Generate a list or a set of strings:

```python
gen = StringGen(r'[A-Z]{3}-\d{3}')

# List (may contain duplicates)
print(gen.render_list(5))  # e.g. ['XKR-839', 'BNQ-271', 'JYL-054', 'WMT-692', 'AFZ-418']

# Set (all unique)
gen = StringGen(r'\d')
print(gen.render_set(10))  # {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
```

## What's Next

- [Generation Methods](generation.md) — all methods for producing strings
- [Configuration](configuration.md) — control repeat limits, alphabets, and global settings
- [Regex Syntax](patterns-syntax.md) — supported regex features
