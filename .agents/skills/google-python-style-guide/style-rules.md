# Style rules (§3)

Layout in this repo is owned by **Black** (`line-length = 80`) and **isort** (`profile = "google"`). Apply the rules below when writing or reviewing; do not hand-fight the formatter. Typing details: [typing.md](typing.md).

## 3.1 Semicolons

Do not end lines with `;` or put two statements on one line via `;`.

## 3.2 Line length

- Maximum **80** characters.
- Exceptions: long imports; URLs/paths/flags in comments; long no-whitespace module constants; pylint disable comments.
- No backslash for explicit line continuation — use parentheses/brackets/braces.
- Docstring summary lines must stay ≤80.
- If Black cannot bring a line under 80, exceeding is allowed; break manually when sensible.

## 3.3 Parentheses

- Do not parenthesize `if`/`while` conditions or bare `return (x)`.
- OK for tuples, implied continuation, and 1-tuples `(foo,)`.

## 3.4 Indentation

- 4 spaces; never tabs.
- Wrap with vertical alignment to opener **or** hanging 4-space indent (nothing on first line of hang).
- Closing bracket may sit with the last element or on its own line aligned with the opener.

### 3.4.1 Trailing commas

- Trailing comma when the closing `]`/`)`/`}` is on its own line, and for 1-tuples.
- Trailing comma is a Black/Pyink hint to explode one item per line.

## 3.5 Blank lines

- 2 blank lines between top-level defs.
- 1 blank line between methods and after class docstring before first method.
- No blank line immediately after a `def` line.

## 3.6 Whitespace

- Standard spaces around binary ops; no space inside `()[]{}`; no space before `,`/`:`.
- No spaces around `=` in kwargs/defaults **unless** annotated default: `a: int = 0`.
- Do not column-align tokens across lines.

## 3.7 Shebang

- Most modules: no shebang.
- Main executable may use `#!/usr/bin/env python3` or `#!/usr/bin/python3`.

## 3.8 Comments and docstrings

### Docstrings

- Always `"""..."""`.
- Summary line ≤80, ends with `.` `?` or `!`; blank line then body if more.

### Modules

- License boilerplate + module docstring describing contents/usage.
- Test modules: docstring only if it adds non-obvious info (not `"""Tests for foo."""`).

### Functions and methods

Required if public API, nontrivial size, or non-obvious logic. Enough to call without reading the body. Consistent imperative or descriptive style within a file.

Sections (omit when name+signature suffice):

- `Args:` — name, colon, description; types if unannotated; include `*args`/`**kwargs` names
- `Returns:` / `Yields:` — semantics beyond the annotation; generators use `Yields:`
- `Raises:` — interface-relevant exceptions only (not API-misuse preconditions)

Properties: document like attributes, not “Returns…”.

### Overridden methods

- With `@override`: docstring optional unless behavior/contract changes.
- Without `@override`: docstring required.
- Trivial “See base class.” discouraged when `@override` is enough.

### Classes

- Class docstring; `Attributes:` for public attrs (same format as `Args:`).
- Summarize what the instance **is**.
- Exception subclasses: describe the condition, not “Raised when…”.

### Block / inline comments

- Explain non-obvious **why**; `#` at least 2 spaces from code, then a space.
- Do not narrate what the code obviously does. Use proper punctuation/spelling.

## 3.10 Strings

- Prefer f-string / `%` / `.format()`; single `+` for two strings OK; do not build with many `+`.
- Do not `+=` strings in loops — list + `''.join` or `StringIO`.
- Consistent quote style per file; `"""` for multiline (docstrings always `"""`).
- Prefer `textwrap.dedent` or implicit concatenation to avoid ugly multiline indent.

### Logging

- First arg is a **literal** pattern string with `%` placeholders; values as later args.
- Do **not** pass an f-string as the logging format message.

### Error messages

- Precisely match the condition; make interpolations clear; keep messages greppable.

## 3.11 Files and stateful resources

- Close with `with` (or `contextlib.closing`).
- Do not rely on `__del__` / GC for observable cleanup.

## 3.12 TODO comments

```text
# TODO: <bug-or-context> - explanation.
```

No new `TODO(user):` or `@user` context. Future work needs a date or concrete event.

## 3.13 Imports formatting

- One import per line (multi-symbol OK from `typing` / `collections.abc`).
- Top of file after module docstring; groups most→least generic (see [references.md](references.md)).
- Lex sort within groups; blank line between groups optional.
- Do not special-case same-package imports in new code.

## 3.14 Statements

- One statement per line.
- Optional `if x: y()` only if it fits and there is **no** `else`.
- Never compact `try`/`except` onto fewer lines.

## 3.15 Accessors

- Getters/setters when get/set is nontrivial or costly (`get_foo` / `set_foo`).
- Otherwise public attribute; properties for simple logic.
- Do not rebind an old property to new complex accessors — force a visible break.

## 3.16 Naming

See table in [references.md](references.md).

- Descriptive names; avoid ambiguous abbreviations and type-in-name suffixes.
- Files: `.py` only; never dashes.
- Single letters only for allowed cases (counters, `e` in except, `f` in with, unconstrained private TypeVars, cited math notation).
- Prefer single `_` for internal; discourage `__` mangling.
- Math-heavy code may use short established names with a citation + targeted `pylint: disable=invalid-name`.

## 3.17 Main

```python
def main() -> None:
    ...


if __name__ == '__main__':
    main()
```

With absl: `app.run(main)`. Keep import-safe top level (no side effects for pydoc/tests).

## 3.18 Function length

Prefer small focused functions. ~40 lines is a soft rethink threshold, not a hard cap.
