# String gen

[![PyPI](https://img.shields.io/pypi/v/string-gen?color=%2301a001&label=pypi&logo=version)](https://pypi.org/project/string-gen/)
[![Downloads](https://pepy.tech/badge/string-gen)](https://pepy.tech/project/string-gen)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/string-gen.svg)](https://pypi.org/project/string-gen/)
[![PyPI - Implementation](https://img.shields.io/pypi/implementation/string-gen)](https://github.com/tolstislon/string-gen)

[![Tests](https://github.com/tolstislon/string-gen/workflows/tests/badge.svg)](https://github.com/tolstislon/string-gen/actions/workflows/python-package.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Generate random strings from regular expression patterns.

**string-gen** takes a regex pattern and produces random strings that match it. Common use cases include:

- **Test data generation** — create realistic inputs for unit and integration tests
- **Fixtures** — produce parameterized test fixtures on the fly
- **Fuzzing** — generate semi-structured random inputs for fuzz testing
- **Mock data** — build placeholder data for prototyping and demos

**[Documentation](https://tolstislon.github.io/string-gen/)** | **[API Reference](https://tolstislon.github.io/string-gen/reference/api/)** | **[Cookbook](https://tolstislon.github.io/string-gen/examples/cookbook/)**

## Installation

```bash
pip install string-gen
```

## Quick Start

```python
from string_gen import StringGen

# Basic generation
gen = StringGen(r'(A|B)\d{4}(\.|-)\d{1}')
gen.render()  # e.g. 'B9954.4'

# List of strings
gen = StringGen(r'[A-Z]{3}-\d{3}')
gen.render_list(5)  # e.g. ['XKR-839', 'BNQ-271', 'JYL-054', 'WMT-692', 'AFZ-418']

# Built-in patterns
from string_gen.patterns import UUID4, IPV4
StringGen(UUID4).render()  # e.g. '52aabe4b-01fa-4b33-8976-b53b09f49e72'
StringGen(IPV4).render()   # e.g. '192.168.1.42'

# Custom alphabets
from string_gen.alphabets import CYRILLIC
StringGen(r'\w{10}', alphabet=CYRILLIC).render()  # e.g. 'ёЩкРблнЫйМ'
```

For full documentation visit **[tolstislon.github.io/string-gen](https://tolstislon.github.io/string-gen/)**.

## Changelog

- [Releases](https://github.com/tolstislon/string-gen/releases)

## Contributing

Contributions are very welcome. You might want to:

- Fix spelling errors
- Improve documentation
- Add tests for untested code
- Add new features
- Fix bugs

### Getting started

- Python 3.8+
- [uv](https://docs.astral.sh/uv/)

1. Clone the repository
    ```bash
    git clone https://github.com/tolstislon/string-gen.git
    cd string-gen
    ```
2. Install dev dependencies
    ```bash
    uv sync
    ```
3. Run ruff format
    ```bash
    uv run ruff format
    ```
4. Run ruff check
    ```bash
    uv run ruff check --fix
    ```
5. Run tests
    ```bash
    uv run pytest tests/
    ```
