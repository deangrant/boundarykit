# Dependency Inversion Principle (DIP)

## Rule

**High-level modules must not depend on low-level modules.** Both should depend on abstractions. Abstractions must not depend on details; details depend on abstractions.

## Why

Hard-coding `CreditCardProcessor()` or `SmtpEmailSender()` inside policy classes locks design to one infrastructure choice, blocks testing with fakes, and turns every vendor swap into a core edit.

## Do

- Define an abstraction (`PaymentProcessor`, `NotificationService`) used by the high-level type.
- Inject concretes via the constructor (or a small factory/composition root).
- Let low-level adapters implement the abstraction.

## Don’t

- Instantiating infrastructure inside domain/application services as a fixed concrete.
- Importing and calling low-level SDKs directly from high-level orchestration without a seam.
- Making the abstraction leak vendor-specific types and error models without need.

## Refactor pattern

1. Name the capability the high-level code needs (process payment, send notice).
2. Extract an ABC or Protocol for that capability.
3. Move the concrete implementation behind it.
4. Construct the graph at the edges (`main`, DI container, test fixtures).

Pairs naturally with SRP (separate roles) and OCP (new adapters without editing policy).

See [examples.md](examples.md#dip).
