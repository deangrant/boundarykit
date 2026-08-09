# Type annotations (§2.21 + §3.19)

## Mandate (§2.21)

- Annotate code, especially public APIs; run a type checker when available.
- Stubs OK for third-party gaps; if blocked, leave a TODO/bug comment.

## 3.19.1 General rules

- Annotate public APIs and error-prone / hard-to-read code; balance safety vs flexibility.
- Usually skip annotating `self` / `cls`; use `Self` when needed for correct typing.
- Do not feel compelled to annotate `__init__` → `None`.
- Use `Any` when expressing the type is not worth it.

## 3.19.2 Line breaking

- Prefer one parameter per line + trailing comma before `) -> Ret`.
- Break between parameters, not between name and annotation.
- Prefer closing `)` aligned with `def`, return type on its own line.
- Last resort: break after `:` and indent the type by 4; prefer a type alias first.

## 3.19.3 Forward declarations

- Use `from __future__ import annotations` or quoted forward refs (`'MyClass'`).

## 3.19.4 Default values

- Spaces around `=` only when both annotation and default are present: `a: int = 0`.

## 3.19.5 NoneType

- Declare nullability explicitly: prefer `X | None` (3.10+); `Optional`/`Union` still OK.
- Do not write `a: str = None`.
- Avoid odd orders like `Union[None, str]`.

## 3.19.6 Type aliases

- CapWords names; module-private `_Alias`.
- Prefer `TypeAlias` annotation on 3.10+.

## 3.19.7 Ignoring types

- `# type: ignore` or `# pytype: disable=...` when needed.

## 3.19.8 Typing variables

- Use annotated assignments: `a: Foo = ...`.
- Do **not** add new `# type: Foo` end-of-line comments.

## 3.19.9 Tuples vs lists

- `list[T]` — homogeneous.
- `tuple[T, ...]` — homogeneous variable-length; or fixed `tuple[A, B, C]`.

## 3.19.10 Type variables

- Descriptive names unless private **and** unconstrained (`_T`, `_P`).
- Constrained/bound TypeVars need real names (`AddableType`), not `_T`.

## 3.19.11 String types

- `str` for text, `bytes` for binary; do not use `typing.Text` in new code.
- Use `AnyStr` when args/return must share the same str-or-bytes type.

## 3.19.12 Imports for typing

- **Exempt from §2.2 module-only rule:** import symbols from `typing` / `collections.abc` (multiple per line OK).
- Prefer abstract containers in APIs (`Sequence`, `Mapping`) over concrete `list`/`dict`.
- Prefer builtins `list`/`tuple`/`dict` over `typing.List`/`Tuple`/`Dict`.

## 3.19.13 Conditional imports

- Discourage `TYPE_CHECKING` blocks; prefer refactoring for top-level imports.
- If used: immediately after normal imports; no blank lines in the list; quote types; typing-only symbols.

## 3.19.14 Circular dependencies

- Typing cycles are smells — refactor first.
- Else: `some_mod = Any` alias pattern with a blank line after imports.

## 3.19.15 Generics

- Always parameterize: `Sequence[int]`, not bare `Sequence` (bare ⇒ `Any`).
- If `Any` is truly right, write it explicitly; often a `TypeVar` is better.
