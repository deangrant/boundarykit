---
name: python-solid-guide
description: >-
  Apply SOLID object-oriented design when designing, refactoring, or reviewing
  Python classes and modules. Use for SOLID, SRP, OCP, LSP, ISP, DIP, single
  responsibility, open/closed, Liskov, interface segregation, dependency
  inversion or injection, ABCs, Protocols, and maintainable OOP structure.
---

# Python SOLID Guide

## Announce

Using the python-solid-guide skill for OOP design/review.

## Read order

1. Tier-A checklist below — apply on design and review.
2. Open the principle file that matches the smell:
   - [srp.md](srp.md) — Single Responsibility
   - [ocp.md](ocp.md) — Open/Closed
   - [lsp.md](lsp.md) — Liskov Substitution
   - [isp.md](isp.md) — Interface Segregation
   - [dip.md](dip.md) — Dependency Inversion
3. [examples.md](examples.md) — Violation / Compliant pairs when refactoring
4. [references.md](references.md) — definitions, smell map, Python idioms

## When to apply

Apply when adding or changing classes/modules, especially:

- God-objects mixing domain, I/O, payment, and notifications
- Growing `if`/`elif` switches on type or mode
- Subclasses that raise, no-op, or change base contracts
- Fat interfaces forcing unused methods
- High-level policy that constructs concrete collaborators

**Skip** forcing SOLID onto tiny one-off scripts with no extension or test pressure.

## Review workflow

1. Name each class’s responsibility and **reasons to change**.
2. Prefer **new subtypes / strategies** over editing closed, tested branches.
3. Check subtype **contracts** (inputs accepted, outputs promised, no surprise exceptions).
4. Split fat interfaces; clients depend only on methods they use.
5. Depend on **abstractions**; inject collaborators (constructor injection).
6. After structural refactors, format/lint with the project style skill when relevant.

## Tier A — enforce on OOP edits

- **S** — One concept / one primary reason to change per class
- **O** — Extend behavior with new code; avoid modifying closed switches for every variant
- **L** — Subtypes must be safely substitutable for their base/Protocol
- **I** — Prefer small, role-specific interfaces over one kitchen-sink ABC
- **D** — High-level modules depend on abstractions, not concrete low-level types

## Anti-overengineering

- SRP means **one concept**, not one method per class — avoid a fragmented sea of single-method types.
- Do not invent an ABC/Protocol for a single forever-stable implementation.
- Prefer composition when inheritance breaks substitutability.
- SOLID guides design under change pressure; clarity beats ceremony.

## Additional resources

- [references.md](references.md)
- [srp.md](srp.md)
- [ocp.md](ocp.md)
- [lsp.md](lsp.md)
- [isp.md](isp.md)
- [dip.md](dip.md)
- [examples.md](examples.md)
