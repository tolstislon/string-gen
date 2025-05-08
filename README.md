# String gen

[![PyPI](https://img.shields.io/pypi/v/string-gen?color=%2301a001&label=pypi&logo=version)](https://pypi.org/project/string-gen/)
[![Downloads](https://pepy.tech/badge/string-gen)](https://pepy.tech/project/string-gen)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/string-gen.svg)](https://pypi.org/project/string-gen/)
[![PyPI - Implementation](https://img.shields.io/pypi/implementation/string-gen)](https://github.com/tolstislon/string-gen)  

[![Code style: black](https://github.com/tolstislon/string-gen/workflows/tests/badge.svg)](https://github.com/tolstislon/string-gen/actions/workflows/python-package.yml)

String generator by regex

Installation
----
Install using pip with

```bash
pip install string-gen
```

Example
----

```python
from string_gen import StringGen

generator = StringGen(r'(A|B)\d{4}(\.|-)\d{1}')
print(generator.render())  # B9954.4
print(generator.render())  # A5292-1

generator = StringGen(r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}')
print(generator.render())  # 52aabe4b-01fa-4b33-8976-b53b09f49e72

# Generate list strings
generator = StringGen(r'(A|B)\d{4}(\.|-)\d{1}')
print(generator.render_list(5))  # ['A9046.5', 'A8334.7', 'B5496-6', 'A4207-2', 'A1171-7']

# Return a set of generated unique strings
generator = StringGen(r'\d')
print(generator.render_set(10))  # {'4', '6', '3', '9', '2', '7', '5', '1', '8', '0'}
```

Changelog
----

* [Releases](https://github.com/tolstislon/string-gen/releases)

Contributing
----

#### Contributions are very welcome.

You might want to:

* Fix spelling errors
* Improve documentation
* Add tests for untested code
* Add new features
* Fix bugs

#### Getting started

* python 3.12
* pipenv 2023.11.15+

1. Clone the repository
    ```bash
    git clone https://github.com/tolstislon/string-gen.git
    cd string-gen
   ```
2. Install dev dependencies
    ```bash
    pipenv install --dev
    pipenv shell
   ```
3. Run ruff format
    ```bash
    pipenv run format
   ```
4. Run ruff check
    ```bash
    pipenv run check
   ```
5. Run tests
   ```bash
   pipenv run tests
   ```