# Quick reference

## Definitions

| Principle | One-liner |
|-----------|-----------|
| **SRP** | A class should have one, and only one, reason to change. |
| **OCP** | Open for extension, closed for modification. |
| **LSP** | Subtypes must be substitutable for their base types without breaking callers. |
| **ISP** | Clients must not be forced to depend on methods they do not use. |
| **DIP** | Depend on abstractions, not concretions; both high- and low-level do. |

## Smell → principle

| Smell | Principle |
|-------|-----------|
| Class handles domain + persistence + email/SMS + payments | SRP |
| Adding a variant means editing a long `if`/`elif` / match ladder | OCP |
| Subclass raises `NotImplementedError`, no-ops a base method, or weakens a guarantee | LSP |
| Square/Rectangle or Ostrich/`fly()` hierarchy surprises callers | LSP |
| One ABC with print + scan + fax + staple; simple clients stub unused methods | ISP |
| Policy class does `CreditCardProcessor()` inside `__init__` or methods | DIP |
| Tests require real DB/email because collaborators are hard-coded | DIP |

## Python idioms

| Tool | Use for |
|------|---------|
| `abc.ABC` + `@abstractmethod` | Shared contracts for related implementations |
| `typing.Protocol` | Structural interfaces without inheritance |
| Constructor injection | Pass abstractions into high-level types |
| Composition | Replace awkward inheritance that breaks LSP |
| Strategy / specification objects | OCP-friendly extension points |

Prefer clear names and small modules. After SOLID refactors, apply project formatting/lint via the google-python-style-guide skill when editing this repo.

## Review prompts

1. What is the single change-reason for this class?
2. Can a new variant ship as a new type without editing this file?
3. Can every subtype stand in for the base in existing call sites?
4. Does each client see only the methods it needs?
5. Are concrete infrastructure types injected behind an abstraction?
