# Agent and contributor guidance

Structured conventions for AI agents and humans working in this repository. For
install/CLI usage, see [README.md](README.md). Prefer the linked sources below
over inventing project conventions.

## Docs

- [`.agents/docs/ARCHITECTURE.md`](.agents/docs/ARCHITECTURE.md) — package
  shape, fetch → assemble → simplify → export flow, module map, errors, and
  extension points (read before large refactors)
- [DeepWiki](https://deepwiki.com/deangrant/boundarykit) — indexed project wiki
  (architecture, API, pipeline) for broader cross-file questions

## Rules

- [`.agents/rules/`](.agents/rules/) (symlinked from [`.cursor/rules`](.cursor/rules))
- [`.agents/rules/boundarykit.mdc`](.agents/rules/boundarykit.mdc) — always-on
  policy: uv/unittest tooling, DI, no pylint suppressions, no new runtime deps,
  CI-parity verify commands

## Skills

- [`.agents/skills/`](.agents/skills/) (symlinked from [`.cursor/skills`](.cursor/skills))
- [`.agents/skills/google-python-style-guide/`](.agents/skills/google-python-style-guide/)
  — Google Python style, Black/isort/pylint workflow for this repo
- [`.agents/skills/python-solid-guide/`](.agents/skills/python-solid-guide/) —
  SOLID design when changing classes/modules
- [`.agents/skills/boundarykit-domain/`](.agents/skills/boundarykit-domain/) —
  OSM assembly, simplify invariants, adding exporters, fixtures/tests

## Commands

- [`.agents/commands/`](.agents/commands/) (symlinked from [`.cursor/commands`](.cursor/commands))
- `/check` — run local CI gates (Black, isort, pylint, unittest)

## Hooks

- Config: [`.cursor/hooks.json`](.cursor/hooks.json)
- `afterFileEdit` → [`.agents/hooks/format-python.sh`](.agents/hooks/format-python.sh)
  formats touched `*.py` with Black + isort (fail open; never blocks the agent)
