r"""
Built-in regex patterns for common data formats.

Each constant is a regex pattern string ready to use with :class:`~string_gen.StringGen`.
Patterns avoid ``\w``, ``\d``, ``\s``, ``\W``, ``\D``, ``\S``, and ``.``
shorthand classes to stay independent of the ``alphabet`` parameter.

.. code-block:: python

    from string_gen import StringGen
    from string_gen.patterns import UUID4, IPV4

    StringGen(UUID4).render()   # e.g. '52aabe4b-01fa-4b33-8976-b53b09f49e72'
    StringGen(IPV4).render()    # e.g. '192.168.1.42'
"""

from typing import Final

# Identifiers
UUID4: Final[str] = "[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}"
OBJECT_ID: Final[str] = "[a-f0-9]{24}"

# Network
IPV4: Final[str] = (
    "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\\."
    "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\\."
    "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])\\."
    "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])"
)
IPV6_SHORT: Final[str] = "[a-f0-9]{1,4}(:[a-f0-9]{1,4}){7}"
MAC_ADDRESS: Final[str] = "[a-f0-9]{2}(:[a-f0-9]{2}){5}"

# Web
HEX_COLOR: Final[str] = "#[a-fA-F0-9]{6}"
HEX_COLOR_SHORT: Final[str] = "#[a-fA-F0-9]{3}"
SLUG: Final[str] = "[a-z][a-z0-9]*(-[a-z0-9]+){1,5}"

# Data formats
SEMVER: Final[str] = "(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)"
DATE_ISO: Final[str] = "20[2-3][0-9]-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
TIME_24H: Final[str] = "([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"

# Security / Auth
JWT_LIKE: Final[str] = "[A-Za-z0-9_-]{20,40}\\.[A-Za-z0-9_-]{20,60}\\.[A-Za-z0-9_-]{20,40}"
API_KEY: Final[str] = "(sk|pk)_(live|test)_[a-zA-Z0-9]{20}"
