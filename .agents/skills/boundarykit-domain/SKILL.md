---
name: boundarykit-domain
description: >-
  OSM relation assembly, geometry simplify, exporters, and test fixtures for
  boundarykit. Use when editing client/assembler/simplify/exporters/cli, adding
  a format, or writing geometry tests.
---

# boundarykit domain

Announce when using this skill. Do not restate Google style or SOLID here.

## Pipeline

`OsmApiClient.fetch_relation_full` → `RelationAssembler.assemble` → optional
`GeometrySimplifier.simplify` → `GeometryExporter.export` via
`RelationGeometryService`. CLI wires concretes in `build_service`.

## Assembly

- Way roles: `outer` / `inner` (case-insensitive). Non-geometry roles (label,
  admin_centre, …) are skipped; unknown roles raise `AssemblyError`.
- Nested relations: recursive assemble with cycle detection; shared children
  are OK, true cycles are not.
- Missing members: optional `fetch_missing(relation_id)` merges into the store.
- Inners must fall in exactly one outer (`geometry.point_in_ring`).

## Simplify

- Tolerance is meters under local equirectangular projection; `None` or `<= 0`
  is a no-op.
- Invalid simplified rings (open, too few points, self-intersecting) keep the
  original ring; inners that leave the outer keep the original inner.

## Adding an exporter

1. Implement `format_id`, `file_extension`, and `export` (see
   `exporters/base.py` `GeometryExporter`).
2. Register in `cli.build_service` exporter list (composition root).
3. Add tests in `tests/test_exporters.py` (and service/CLI if wiring matters).

## Tests and fixtures

- Prefer `unittest` + fakes (e.g. fake `urlopen` returning XML bytes).
- OSM XML fixtures live under `tests/fixtures/`.
- Inject `urlopen` / `sleep` / `monotonic` on `OsmApiClient` for deterministic
  client tests; mock `build_service` for CLI exit-code tests.
