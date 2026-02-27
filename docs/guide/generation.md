# Generation Methods

## render()

Produce a single random string matching the pattern.

```python
from string_gen import StringGen

gen = StringGen(r'[a-z]{5}')
gen.render()  # e.g. 'qmxbr'
```

## render_list()

Produce a list of `count` random strings. May contain duplicates.

```python
gen = StringGen(r'\d{3}')
gen.render_list(3)  # e.g. ['847', '192', '503']
```

## render_set()

Produce a set of `count` **unique** strings. Raises `StringGenMaxIterationsReachedError` if the iteration limit is reached before collecting enough unique values.

```python
gen = StringGen(r'[01]')
gen.render_set(2)  # {'0', '1'}
```

The optional `max_iteration` parameter controls the maximum number of generation attempts (default: 100,000):

```python
gen = StringGen(r'\d')
gen.render_set(10, max_iteration=1_000)  # raises early if unlucky
```

If the pattern cannot produce enough unique strings, a `ValueError` is raised immediately:

```python
gen = StringGen(r'[ab]')
gen.render_set(5)  # ValueError: Cannot generate 5 unique strings: pattern can only produce 4
```

## Iteration

`StringGen` instances are iterable. Iterating yields an **infinite** stream of random matching strings:

```python
gen = StringGen(r'\d{4}')

for value in gen:
    print(value)  # e.g. '8374'
    break  # without break, iterates forever
```

Works with `itertools`:

```python
from itertools import islice

gen = StringGen(r'\d{4}')
values = list(islice(gen, 10))  # 10 random strings
```

## stream()

Return a lazy iterator that yields `count` random strings one at a time. Memory-efficient alternative to `render_list` for large batches:

```python
gen = StringGen(r'\d{4}')
for value in gen.stream(1000):
    process(value)
```

## count()

Return the number of unique strings the pattern can produce. Returns `math.inf` for patterns with unbounded quantifiers (`*`, `+`, `{n,}`). The result is cached after the first call.

```python
gen = StringGen(r'[01]{3}')
gen.count()  # 8

gen = StringGen(r'\d')
gen.count()  # 10

gen = StringGen(r'\w+')
gen.count()  # math.inf
```

## enumerate()

Yield **all** unique strings the pattern can produce. Useful for exhaustive testing over finite patterns.

```python
gen = StringGen(r'[ab]{2}')
list(gen.enumerate())  # ['aa', 'ab', 'ba', 'bb']

gen = StringGen(r'(yes|no)')
list(gen.enumerate())  # ['yes', 'no']
```

For patterns with unbounded quantifiers, `limit` caps the maximum repetition count. When `limit` is `None`, the parser's `max_repeat` value is used:

```python
gen = StringGen(r'\d+')
list(gen.enumerate(limit=1))  # ['0', '1', ..., '9']
```
