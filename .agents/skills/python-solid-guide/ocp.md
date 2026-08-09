# Open/Closed Principle (OCP)

## Rule

Software entities should be **open for extension** and **closed for modification**: add behavior with new code, not by endlessly editing stable, tested branches.

## Why

Every new payment, delivery, or search mode that requires editing a central switch risks regressions and retesting. Extension via new subtypes keeps existing paths stable.

## Do

- Introduce an ABC/Protocol for the variation point (`Delivery`, `PaymentProcessor`, `SearchBy`).
- Add variants as new subclasses/strategies; callers depend on the abstraction.
- Use composition (e.g. combinable search specs) when combinations would explode method counts.

## Don’t

- Grow `if method == "post" / "email" / "drone"` ladders in a single processor for every new mode.
- Copy-paste nearly identical methods (`search_by_artist`, `search_by_genre`, …) for each filter dimension.
- Modify closed library/core classes for each product feature when a plugin/strategy hook exists.

## Refactor pattern

1. Identify the axis of change (delivery method, payment rail, search criterion).
2. Extract a small interface with one clear operation (`deliver`, `process`, `is_matched`).
3. Move each branch into its own implementation.
4. Keep the orchestrator closed; inject or register new implementations.

See [examples.md](examples.md#ocp).
