# Quick reference

## Section → file

| Topic | File |
|-------|------|
| Lint, imports, packages, exceptions, globals, nesting, comprehensions, iterators, generators, lambdas, ternaries, defaults, properties, truthiness, scoping, decorators, threading, power features, `__future__` | [language-rules.md](language-rules.md) |
| Semicolons, line length, parens, indent, blanks, whitespace, shebang, comments/docstrings, strings/logging, files, TODO, import format, statements, accessors, naming, main, function length | [style-rules.md](style-rules.md) |
| Type annotations (§2.21 + §3.19) | [typing.md](typing.md) |
| Yes/No code pairs | [examples.md](examples.md) |

## Formatter and lint (this repo)

| Tool | Config | Role |
|------|--------|------|
| uv | `pyproject.toml` `[tool.uv]`, `uv.lock` | Package manager; `uv sync --group dev` |
| Black | `pyproject.toml` `[tool.black]` | Auto-format; `line-length = 80` |
| isort | `pyproject.toml` `[tool.isort]` `profile = "google"` | Import order/groups |
| pylint | `.pylintrc` | Canonical Google-style lint (do not replace) |
| Editor | `.vscode/settings.json`, `.editorconfig` | Format on save / indent |

```bash
uv sync --group dev
uv run black .
uv run isort .
uv run pylint --rcfile=.pylintrc <paths>
```

Do not override Black’s wrapping for cosmetic preference. Do not add `[tool.pylint]` that fights `.pylintrc`.

## Naming

| Type | Public | Internal |
|------|--------|----------|
| Packages / modules | `lower_with_under` | `_lower_with_under` |
| Classes / exceptions | `CapWords` | `_CapWords` (classes) |
| Functions / methods | `lower_with_under()` | `_lower_with_under()` |
| Constants | `CAPS_WITH_UNDER` | `_CAPS_WITH_UNDER` |
| Vars / params | `lower_with_under` | `_lower_with_under` |

Avoid: dashes in filenames, type-in-name (`id_to_name_dict`), offensive names, dunder-private for “privacy”, ambiguous abbreviations.

Unit tests: `test_<method>_<state>` (or legacy `test<Method>_<state>`).

## Import groups (top → bottom)

1. `__future__`
2. Stdlib
3. Third-party
4. Project / repo packages

One import per line (exception: multiple symbols from `typing` / `collections.abc`). Lex sort within group. No relative imports. No separate “same-package” section for new code.

## TODO format

```python
# TODO: crbug.com/192795 - Investigate cpufreq optimizations.
```

Discouraged: `TODO(user):`, `@user` as context. Future work needs a date or concrete event.

## pylint suppress

```python
def do_PUT(self):  # WSGI name, so pylint: disable=invalid-name
    ...

def viking_cafe_order(spam: str, beans: str, eggs: str | None = None) -> str:
    del beans, eggs  # Unused.
    return spam + spam + spam
```

Prefer `pylint: disable=` over `disable-msg`. Add a reason when the symbol alone is unclear. `_` / `unused_` unused-arg forms are allowed but no longer encouraged.

## Agent pitfalls

| Trap | Correct |
|------|---------|
| Rewrite `from collections.abc import Sequence` to module-only import | Typing-stack symbol imports are exempt |
| `from . import foo` | Full package path; no relative imports |
| Spaces around `=` always / never | Spaces only when annotation **and** default: `a: int = 0` |
| `logger.info(f'...')` | `logger.info('...%s', value)` |
| `assert` for API validation | Raise `ValueError` (etc.); asserts OK in pytest |
| `@staticmethod` helpers | Module-level function |
| Double-`for` comprehensions | Nested loops |
| Bare `Sequence` / `list` | `Sequence[T]` / `list[T]` |
| `a: str = None` | `a: str | None = None` |
| Fighting Black to hit 80 | Trust Black; exceed only if formatter cannot help |
