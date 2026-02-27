# Built-in Patterns

The `string_gen.patterns` module provides ready-to-use regex patterns for common data formats.

## Usage

```python
from string_gen import StringGen
from string_gen.patterns import UUID4, IPV4, SEMVER

StringGen(UUID4).render()   # e.g. '52aabe4b-01fa-4b33-8976-b53b09f49e72'
StringGen(IPV4).render()    # e.g. '192.168.1.42'
StringGen(SEMVER).render()  # e.g. '2.14.3'
```

## Available Patterns

### Identifiers

| Preset | Example output | Description |
|--------|----------------|-------------|
| `UUID4` | `52aabe4b-01fa-4b33-8976-b53b09f49e72` | UUID version 4 |
| `OBJECT_ID` | `507f1f77bcf86cd799439011` | MongoDB ObjectId (24 hex chars) |

### Network

| Preset | Example output | Description |
|--------|----------------|-------------|
| `IPV4` | `192.168.1.42` | IPv4 address (valid 0-255 octets) |
| `IPV6_SHORT` | `a3f2:b1c4:5d6e:4f7a:8b9c:0d1e:2f3a:4b5c` | IPv6 address (simplified, no `::`) |
| `MAC_ADDRESS` | `a3:f2:b1:c4:5d:6e` | MAC address |

### Web

| Preset | Example output | Description |
|--------|----------------|-------------|
| `HEX_COLOR` | `#a3f2b1` | Hex color (6 digits) |
| `HEX_COLOR_SHORT` | `#a3f` | Hex color (3 digits) |
| `SLUG` | `my-awesome-post` | URL slug |

### Data Formats

| Preset | Example output | Description |
|--------|----------------|-------------|
| `SEMVER` | `2.14.3` | Semantic versioning |
| `DATE_ISO` | `2024-03-15` | ISO 8601 date (2020-2039) |
| `TIME_24H` | `14:32:07` | 24-hour time |

### Security / Auth

| Preset | Example output | Description |
|--------|----------------|-------------|
| `JWT_LIKE` | `eyJhb...eyJzd...SflKx` | JWT-like token structure |
| `API_KEY` | `sk_live_a3f2b1c45d6e4f7a8b9c` | Stripe-like API key |

!!! note
    All patterns avoid `\w`, `\d`, `\s`, `.` shorthand classes, so they work correctly regardless of the `alphabet` setting.
