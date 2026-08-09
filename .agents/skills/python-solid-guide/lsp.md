# Liskov Substitution Principle (LSP)

## Rule

Subtypes must be **substitutable** for their base types: any code that works with the base must keep working correctly with the subtype.

## Why

Callers program to the base contract. If a subtype changes geometry invariants, refuses a base capability, or alters expected results, polymorphic code becomes unsafe and surprising.

## Do

- Preserve preconditions (don’t require more) and postconditions (don’t promise less).
- Keep method signatures and semantic guarantees aligned with the base/Protocol.
- Split hierarchies when behaviors diverge (`FlyingBird` vs non-flying `Bird`; shape traits vs mutable width/height rectangles).
- Prefer composition when “is-a” inheritance breaks behavioral expectations.

## Don’t

- Override with `raise Exception("cannot…")` for a capability the base advertises (`Ostrich.fly`).
- Make `Square` inherit mutable independent `width`/`height` setters from `Rectangle` if that breaks area assumptions.
- Model restricted actors (e.g. `Prisoner`) as subtypes that silently no-op movement APIs of a free `Person`.

## Refactor pattern

1. Write a client that uses only the base type’s contract.
2. Run it with each subtype — failures indicate LSP breaks.
3. Either narrow the base interface to true shared behavior, or stop inheriting and compose instead.

See [examples.md](examples.md#lsp).
