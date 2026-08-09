# Single Responsibility Principle (SRP)

## Rule

A class should have **one primary reason to change** — one cohesive concept or responsibility, not a grab-bag of unrelated jobs.

## Why

Mixed responsibilities couple unrelated change drivers (e.g. file I/O vs compression, order creation vs payment vs notifications). That makes tests harder, reuse poorer, and edits riskier (side effects in unrelated features).

## Do

- Split by change reason: `FileManager` (read/write) vs `ZipArchiver` (compress/decompress).
- Split domain from side effects: `FoodOrder` vs `PaymentProcessor` vs `NotificationSender`.
- Keep a class focused on one concept even if it has several related methods (`add_song` / `remove_song` on an album model is fine).

## Don’t

- Park search/DB browsing on a domain entity that only models album state.
- Build “manager” god-classes that create orders, charge cards, and send email.
- Over-split into one-method micro-classes that force readers through a long call chain for a single idea.

## Refactor pattern

1. List methods and the external forces that would force each to change.
2. Group methods that share the same change reason.
3. Extract groups into named types; keep the original type for its core concept.
4. Wire collaborators explicitly (often pairs with DIP).

See [examples.md](examples.md#srp).
