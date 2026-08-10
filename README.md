# boundarykit

boundarykit builds **multipolygon geometry** for an OpenStreetMap **relation**.
A relation may include ways and nested sub-relations.
The package can simplify rings and export **poly**, **GeoJSON**, **WKT**, or
**SVG**.

## Technical overview

boundarykit works in four steps.

1. Fetch `relation/{id}/full` from the OSM API 0.6 and parse the XML into an
   element store.
2. Assemble a multipolygon from outer and inner rings. Nested relations are
   included when needed.
3. Optionally simplify rings with Douglas–Peucker in local meters.
4. Export one or more formats to disk.

The CLI wires the collaborators and runs the workflow.
Library callers can inject the same pieces into `RelationGeometryService`.

## Requirements

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)
- Network access to the OSM API (or a custom `--base-url` for tests)
- No third-party **runtime** dependencies (stdlib only)

## Install

Clone the repository, then sync the environment.

```bash
git clone https://github.com/deangrant/boundarykit.git
cd boundarykit
uv sync
```

Install development tools (Black, isort, pylint) as well.

```bash
uv sync --group dev
```

Run the CLI with uv.

```bash
uv run boundarykit --help
uv run python -m boundarykit --help
```

## CLI usage

### One format to one file

```bash
uv run boundarykit 123456 -f geojson -o out.geojson
```

`--output` / `-o` requires a **single** format. For several formats, use
`--output-dir`.

### Several formats to a directory

```bash
uv run boundarykit 123456 -f poly,geojson,wkt --output-dir ./out
```

Printed lines are the written paths.
File names use a sanitized relation name when present, otherwise
`relation_<id>`.

### Simplify and preview

```bash
uv run boundarykit 123456 --simplify 5 -f svg -o preview.svg
```

`--simplify` is a tolerance in **meters** under a local equirectangular
projection.
Omit it, or use a value `<= 0`, to skip simplification.

### WKT / EWKT and GeoJSON Feature

```bash
uv run boundarykit 123456 -f wkt --ewkt -o area.wkt
uv run boundarykit 123456 -f geojson --geojson-feature -o area.geojson
```

### Options

| Option | Meaning |
| ------ | ------- |
| `relation_id` | OSM relation id (required) |
| `-f` / `--format` | Comma-separated formats: `poly`, `geojson`, `wkt`, `svg` (default: `geojson`) |
| `-o` / `--output` | Output file for a single format |
| `--output-dir` | Output directory for one or more formats |
| `--simplify METERS` | Optional Douglas–Peucker tolerance in meters |
| `--ewkt` | Prefix WKT with `SRID=4326` |
| `--geojson-feature` | Wrap GeoJSON MultiPolygon in a Feature |
| `--base-url` | Override OSM API base URL (for testing) |
| `-v` / `--verbose` | Debug logging |

## Library usage

Inject collaborators into `RelationGeometryService`, then call `run` (or
`build_geometry` and `export` separately).

```python
from pathlib import Path

from boundarykit import assembler
from boundarykit import client
from boundarykit import service
from boundarykit import simplify
from boundarykit.exporters import geojson
from boundarykit.exporters import poly

osm_client = client.OsmApiClient()
relation_assembler = assembler.RelationAssembler(
    fetch_missing=osm_client.fetch_relation_full
)
geometry_service = service.RelationGeometryService(
    osm_client=osm_client,
    relation_assembler=relation_assembler,
    geometry_simplifier=simplify.GeometrySimplifier(),
    exporters={
        "poly": poly.PolyExporter(),
        "geojson": geojson.GeoJsonExporter(),
    },
)
paths = geometry_service.run(
    123456,
    ["geojson"],
    simplify_tolerance=5.0,
    output=Path("out.geojson"),
)
```

For module roles, errors, and extension points, see
[.agents/docs/ARCHITECTURE.md](.agents/docs/ARCHITECTURE.md).

## Export formats

| Format id | Extension | Notes |
| --------- | --------- | ----- |
| `poly` | `.poly` | Osmosis-compatible polygon file |
| `geojson` | `.geojson` | MultiPolygon; use `--geojson-feature` for a Feature |
| `wkt` | `.wkt` | WKT multipolygon; use `--ewkt` for EWKT |
| `svg` | `.svg` | Simple preview map |

## Develop

Format, lint, and test with the same commands as CI.

```bash
uv sync --locked --group dev
uv run black --check src tests
uv run isort --check-only src tests
uv run pylint --rcfile=.pylintrc src/boundarykit tests
uv run python -m unittest discover -s tests -v
```

GitHub Actions runs lint on Python 3.11 and tests on Python 3.11–3.13.

## Further reading

- [AGENTS.md](AGENTS.md) — agent and contributor index
- [.agents/docs/ARCHITECTURE.md](.agents/docs/ARCHITECTURE.md) — system architecture
- [DeepWiki](https://deepwiki.com/deangrant/boundarykit) — indexed project wiki
