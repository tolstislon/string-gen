from .generator import (
    StringGen,
    StringGenError,
    StringGenPatternError,
    StringGenMaxIterationsReachedError,
)

try:
    from .__version__ import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

__all__ = [
    "__version__",
    "StringGen",
    "StringGenError",
    "StringGenPatternError",
    "StringGenMaxIterationsReachedError",
]
