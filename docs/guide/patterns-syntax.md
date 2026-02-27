# Regex Syntax

## Supported Features

| Feature | Syntax | Example |
|---------|--------|---------|
| Literals | `abc` | `abc` |
| Dot (any character) | `.` | `.{5}` |
| Character classes | `[abc]`, `[a-z]`, `[^0-9]` | `[A-Za-z_]` |
| Shorthand classes | `\d`, `\D`, `\w`, `\W`, `\s`, `\S` | `\d{4}` |
| Negated literal | `[^x]` | `[^a]` |
| Quantifiers | `{n}`, `{n,m}`, `*`, `+`, `?` | `\w{3,8}` |
| Lazy quantifiers | `{n,m}?`, `*?`, `+?`, `??` | `\d{1,5}?` |
| Groups | `(...)` | `(abc)` |
| Alternation | `a\|b` | `(yes\|no)` |
| Backreferences | `\1`, `\2` | `(a)\1` |
| Anchors | `^`, `$` | `^\d+$` |
| Lookahead | `(?=...)` | `(?=prefix)` |
| Negative lookahead | `(?!...)` | `(?!skip)` |

## Limitations

- **Unbounded quantifiers capped** — `*`, `+`, and `{n,}` default to 100 repetitions (configurable via `max_repeat` or `configure()`)
- **No conditional backreferences** — `(?(id)yes|no)` syntax is not supported
- **Anchors are ignored** — `^` and `$` do not constrain output; they are treated as empty strings
- **Negative lookahead is ignored** — `(?!...)` always produces an empty string
- **Not a regex validator** — the library generates strings matching the parsed AST, but does not guarantee coverage of all possible matches
