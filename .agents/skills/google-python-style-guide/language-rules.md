# Language rules (§2)

Decisions only. See [examples.md](examples.md) for Yes/No pairs.

## 2.1 Lint

- Run pylint with the project rc (this repo: `.pylintrc`).
- Suppress with `# pylint: disable=symbol`; add a reason when unclear.
- Prefer `disable=` over deprecated `disable-msg`.
- Unused args: `del name  # Unused.` at start of body (preferred over `_` / `unused_`).

## 2.2 Imports

- Import packages/modules only: `import x`, `from x import y` (y = module).
- `as` for collisions, long/generic names, or standard abbreviations (`numpy as np`).
- **No relative imports** — always full package path.
- **Exemptions** (may import symbols): `typing`, `collections.abc`, `typing_extensions`, and `six.moves` redirects.

## 2.3 Packages

- Import by full package path (`from doctor.who import jodie`).
- Do not bare-import a local sibling as if top-level (`import jodie` when meaning local `jodie.py`).

## 2.4 Exceptions

- Prefer built-ins when apt; custom exceptions end in `Error`, inherit existing types.
- Do not use `assert` for required application logic (pytest asserts OK).
- No bare `except:`; catch `Exception` only to re-raise or at a true isolation boundary.
- Minimize `try` body; use `finally` / context managers for cleanup.
- Do not document precondition-violation exceptions in `Raises:`.

## 2.5 Mutable global state

- Avoid mutating module/class globals.
- Constants OK (`CAPS_WITH_UNDER`).
- Rare mutable globals: `_name`, accessors, justify in a comment.

## 2.6 Nested classes / functions

- Nest only to close over a local other than `self`/`cls`.
- For privacy/testability, use module-level `_helper` instead of nesting to hide.

## 2.7 Comprehensions

- Allowed for simple cases.
- **Forbidden:** multiple `for` clauses or multiple filters — use nested loops.

## 2.8 Default iterators

- Prefer `for k in d`, `for line in f`, `.items()`.
- Avoid `.keys()` / `.readlines()` just to iterate.
- Do not mutate a container while iterating over it.

## 2.9 Generators

- Fine to use; docstring section is `Yields:` not `Returns:`.
- Expensive resources: force cleanup (context manager around the generator).

## 2.10 Lambdas

- One-liners only; longer → nested `def`.
- Prefer genexps over `map`/`filter` + lambda; prefer `operator.*` for trivial ops.

## 2.11 Conditional expressions

- OK when true / if / else each fit one line (or approved multi-line shapes).
- Otherwise use a full `if` statement.

## 2.12 Default argument values

- Defaults OK.
- **Never** mutable defaults (`[]`, `{}`) or call-time values (`time.time()`, flags) as defaults.

## 2.13 Properties

- `@property` only for cheap, unsurprising, trivial derived or controlled access.
- Do not wrap plain attribute get/set; do not use for subclass-overridable logic.
- Manual descriptors count as power features.

## 2.14 True/False evaluations

- Prefer implicit truthiness (`if foo:`, `if not seq:`).
- Always `is None` / `is not None`.
- Never compare to `False` with `==`.
- Integers: compare to `0` explicitly when needed (`if i % 10 == 0`, not `if not i % 10`).
- Numpy: prefer `.size` over truthiness of arrays.

## 2.16 Lexical scoping

- Closures OK.
- Assignment to a name makes it local for the whole function — watch loop-variable / late-binding bugs.

## 2.17 Decorators

- Use when the win is clear; document and test.
- Avoid heavy import-time side effects in decorators.
- **Never `staticmethod`** — prefer a module-level function (unless an external API requires it).
- **`classmethod`** only for named constructors or class-global state (e.g. process-wide cache).

## 2.18 Threading

- Do not rely on built-in atomicity.
- Prefer `queue.Queue`; else `threading` with `Condition` over low-level locks.

## 2.19 Power features

- Avoid metaclasses, bytecode hacks, import hacks, reflection abuse, custom `__del__` cleanup, etc.
- Stdlib that uses them internally (`abc`, `dataclasses`, `enum`) is fine.

## 2.20 `from __future__` imports

- Use when helpful; keep until the runtime floor makes them unnecessary.
- Prefer modern 3.10+ language defaults for new code.

## 2.21 Type annotated code

- Annotate (especially public APIs) and type-check.
- Stubs OK for third-party; if blocked, leave a TODO/bug comment.
- Mechanics: [typing.md](typing.md).
