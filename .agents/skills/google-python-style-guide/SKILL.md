---
name: google-python-style-guide
description: >-
  Apply Google Python language, style, and typing rules when writing, editing,
  reviewing, formatting, or linting Python. Use for Google style, Black,
  isort, pylintrc, docstrings (Args/Returns/Yields/Raises), imports, naming,
  and type annotations.
---

# Google Python Style Guide

## Announce

Using the google-python-style-guide skill for Python write/review/format.

## Read order

1. Tier-A checklist below — enforce on every edit.
2. Topic detail only as needed:
   - [language-rules.md](language-rules.md) — §2 language decisions
   - [style-rules.md](style-rules.md) — §3 formatting, docs, naming, main
   - [typing.md](typing.md) — §2.21 + §3.19
3. [examples.md](examples.md) — Yes/No pairs when writing or correcting a pattern
4. [references.md](references.md) — naming table, import order, TODO, formatter commands

## Workflow (this repo)

1. **Format first** — Black + isort via root `pyproject.toml` (`line-length = 80`), run with uv. Do not hand-fight Black on cosmetics.
2. **Lint** — `uv run pylint --rcfile=.pylintrc <paths>` (existing Google-style rc; do not replace it).
3. **80-column exceptions** — long imports, URLs/paths in comments, long no-whitespace constants, pylint disables. If Black cannot bring a line under 80, exceeding is allowed; break manually when sensible.
4. **Local consistency** — match surrounding style for non-cosmetic conflicts; prefer modern guide rules for new code.

```bash
uv sync --group dev
uv run black .
uv run isort .
uv run pylint --rcfile=.pylintrc <paths>
```

## Tier A — enforce every edit

- **Imports** — packages/modules only; full package paths; no relative imports; `typing` / `collections.abc` / `typing_extensions` symbol imports OK; groups: `__future__` → stdlib → third-party → project; lex sort within groups
- **Defaults** — no mutable default args (`[]`, `{}`); no call-time defaults like `time.time()`
- **Exceptions** — no bare `except:`; catch `Exception` only to re-raise or isolate; no `assert` for production validation (pytest OK)
- **Resources** — close files/sockets via `with` (or `contextlib.closing`)
- **Types** — annotate public APIs; use `X | None`; parameterize generics (`Sequence[str]`, not bare `Sequence`)
- **Naming** — `snake_case` modules/functions, `CapWords` classes/exceptions, `CAPS` constants, `_` for internal
- **Docstrings** — public / nontrivial / non-obvious; sections `Args:` / `Returns:` or `Yields:` / `Raises:` as needed; summary ≤80 chars ending `.?!`
- **Logging** — literal pattern + args (`logger.info('x=%s', x)`), not f-string as first arg
- **Main** — executable logic in `main()` behind `if __name__ == '__main__'`
- **Comprehensions** — simple only; no multiple `for` / filter clauses
- **pylint** — `# pylint: disable=symbol` (+ reason if unclear); unused args: `del x  # Unused.`

## Tier B — flag in review

- Properties only for cheap, unsurprising access; plain attrs when get/set is trivial
- Never `staticmethod` (prefer module function); `classmethod` only for named constructors / class-global state
- Implicit truthiness OK; always `is None` / `is not None`; never `== False`; careful with ints / Numpy
- Avoid power features (metaclasses, import hacks, custom `__del__` cleanup, etc.)
- No string `+=` in loops — list + `join` or `StringIO`
- Soft rethink at ~40 lines per function
- TODO: `# TODO: <bug-or-context> - explanation.`
- `@override`: docstring optional unless contract changes; without `@override`, docstring required

## Additional resources

- [references.md](references.md)
- [language-rules.md](language-rules.md)
- [style-rules.md](style-rules.md)
- [typing.md](typing.md)
- [examples.md](examples.md)
