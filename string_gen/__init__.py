r"""
String Generator.

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
"""

from .generator import (
    StringGen,
    StringGenError,
    StringGenMaxIterationsReachedError,
    StringGenPatternError,
)

try:
    from .__version__ import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

__all__ = [
    "StringGen",
    "StringGenError",
    "StringGenMaxIterationsReachedError",
    "StringGenPatternError",
    "__version__",
]
