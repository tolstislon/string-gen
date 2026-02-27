# string-gen

Generate random strings from regular expression patterns.

**string-gen** takes a regex pattern and produces random strings that match it. Common use cases include test data generation, fixtures, fuzzing, and mock data.

## Installation

```bash
pip install string-gen
```

## Quick Example

```python
from string_gen import StringGen

gen = StringGen(r'(A|B)\d{4}(\.|-)\d{1}')
print(gen.render())  # e.g. B9954.4

gen = StringGen(r'[A-Z]{3}-\d{3}')
print(gen.render_list(5))  # e.g. ['XKR-839', 'BNQ-271', 'JYL-054', 'WMT-692', 'AFZ-418']
```

## Next Steps

- [Getting Started](guide/getting-started.md) — installation, basic usage, reproducible output
- [Generation Methods](guide/generation.md) — `render`, `render_list`, `render_set`, `stream`, `count`, `enumerate`
- [Configuration](guide/configuration.md) — `max_repeat`, custom alphabets, `configure()`, `reset()`
- [Regex Syntax](guide/patterns-syntax.md) — supported regex features and limitations
- [API Reference](reference/api.md) — full API docs with signatures and parameters
- [Built-in Patterns](reference/patterns.md) — UUID, IPv4, JWT, and more
- [Alphabet Presets](reference/alphabets.md) — Cyrillic, Greek, CJK, and 19 other scripts
- [Cookbook](examples/cookbook.md) — recipes for common scenarios
