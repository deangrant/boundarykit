# Interface Segregation Principle (ISP)

## Rule

Prefer **many small, client-specific interfaces** over one fat interface. Clients should not depend on methods they do not use.

## Why

Fat interfaces force implementers to stub unused operations and couple clients to irrelevant change. Small role interfaces keep implementations honest and clients focused.

## Do

- Split capabilities: `Printer` / `Scanner` (and compose for multi-function devices).
- Split payment rails: `CardPayment` / `CashPayment` / `UpiPayment` instead of one mega-`Payment`.
- Use `Protocol` or narrow ABCs so each client imports only what it needs.

## Don’t

- Require every device to implement print + scan + fax + staple.
- Force cash-only handlers to implement `pay_by_card` / `pay_by_upi` no-ops.
- Grow a “god Protocol” with unrelated lifecycle methods “just in case.”

## Refactor pattern

1. List clients and the methods each actually calls.
2. Cluster methods by client need into separate interfaces.
3. Let rich implementations inherit/implement multiple small interfaces.
4. Retarget clients at the smallest interface that satisfies them.

See [examples.md](examples.md#isp).
