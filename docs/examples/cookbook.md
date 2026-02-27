# Cookbook

Practical recipes for common string generation scenarios.

## UUID

```python
from string_gen import StringGen
from string_gen.patterns import UUID4

gen = StringGen(UUID4)
gen.render()  # e.g. '52aabe4b-01fa-4b33-8976-b53b09f49e72'
```

## Email-like Strings

```python
gen = StringGen(r'[a-z]{5,10}@(gmail|yahoo|outlook)\.com')
gen.render()  # e.g. 'hqxvmr@gmail.com'
```

## API Testing

```python
from string_gen.patterns import API_KEY, JWT_LIKE

# Stripe-like API key
gen = StringGen(API_KEY)
gen.render()  # e.g. 'sk_live_a3f2b1c45d6e4f7a8b9c'

# JWT-like token
gen = StringGen(JWT_LIKE)
gen.render()  # e.g. 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkw.SflKxwRJSMeKKF2QT4fwp'
```

## Network Addresses

```python
from string_gen.patterns import IPV4, MAC_ADDRESS

gen = StringGen(IPV4)
gen.render()  # e.g. '192.168.1.42'

gen = StringGen(MAC_ADDRESS)
gen.render()  # e.g. 'a3:f2:b1:c4:5d:6e'
```

## i18n Testing

```python
from string_gen import StringGen
from string_gen.alphabets import CYRILLIC, CJK, GREEK

# Russian text
gen = StringGen(r'\w{10}', alphabet=CYRILLIC)
gen.render()  # e.g. 'ёЩкРблнЫйМ'

# Chinese characters
gen = StringGen(r'\w{5}', alphabet=CJK)
gen.render()  # e.g. '漢字生成器'

# Greek text
gen = StringGen(r'\w{8}', alphabet=GREEK)
gen.render()  # e.g. 'αβγδεζηθ'
```

## Exhaustive Testing

Generate **all** possible values for a finite pattern:

```python
gen = StringGen(r'[ab]{2}')

# Check total count
gen.count()  # 4

# Enumerate all combinations
list(gen.enumerate())  # ['aa', 'ab', 'ba', 'bb']
```

Use `enumerate` with `limit` for patterns that have unbounded quantifiers:

```python
gen = StringGen(r'\d+')
list(gen.enumerate(limit=1))  # ['0', '1', '2', ..., '9']
```

## Reproducible Data

Use `seed` for deterministic output across runs:

```python
gen = StringGen(r'[A-Z]{3}-\d{3}', seed=42)
gen.render()  # always produces the same string

# Re-seed to replay the sequence
gen.seed(42)
gen.render()  # same string again
```

## Combining Patterns

Use `|` to concatenate patterns:

```python
prefix = StringGen(r'[A-Z]{3}')
suffix = StringGen(r'\d{4}')

combined = prefix | suffix
combined.render()  # e.g. 'XKR8374'
```

!!! note
    The `|` operator strips trailing `$` from the left pattern and leading `^` from the right pattern before concatenation.

## Batch Generation

For large batches, `stream` is more memory-efficient than `render_list`:

```python
gen = StringGen(r'\d{10}')

# Memory-efficient: yields one at a time
for value in gen.stream(100_000):
    process(value)

# Collects all into a list at once
values = gen.render_list(100_000)
```

## Unique Constraints

Combine `render_set` with `count` to safely generate unique values:

```python
gen = StringGen(r'[A-F]\d')

# Check if enough unique strings are possible
available = gen.count()  # 60
assert available >= 10

# Generate 10 unique strings
unique = gen.render_set(10)
print(unique)  # e.g. {'A3', 'B7', 'C1', 'D4', 'E9', 'F0', 'A8', 'B2', 'C5', 'D6'}
```
