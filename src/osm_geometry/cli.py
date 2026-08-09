"""Command-line interface for osm-geometry."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from osm_geometry.assembler import AssemblyError
from osm_geometry.assembler import RelationAssembler
from osm_geometry.client import OsmApiClient
from osm_geometry.client import OsmClientError
from osm_geometry.exporters.geojson import GeoJsonExporter
from osm_geometry.exporters.poly import PolyExporter
from osm_geometry.exporters.svg import SvgExporter
from osm_geometry.exporters.wkt import WktExporter
from osm_geometry.service import RelationGeometryService
from osm_geometry.simplify import GeometrySimplifier


def build_parser() -> argparse.ArgumentParser:
    """Returns the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="osm-geometry",
        description=(
            "Build full geometry for an OpenStreetMap relation (including "
            "sub-relations) and export poly, GeoJSON, WKT, or SVG."
        ),
    )
    parser.add_argument(
        "relation_id",
        type=int,
        help="OSM relation id",
    )
    parser.add_argument(
        "-f",
        "--format",
        dest="formats",
        default="geojson",
        help="Comma-separated formats: poly,geojson,wkt,svg (default: geojson)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file when exporting a single format",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory when exporting one or more formats",
    )
    parser.add_argument(
        "--simplify",
        type=float,
        default=None,
        metavar="DEG",
        help="Optional Douglas–Peucker tolerance in degrees",
    )
    parser.add_argument(
        "--ewkt",
        action="store_true",
        help="Prefix WKT with SRID=4326 (EWKT)",
    )
    parser.add_argument(
        "--geojson-feature",
        action="store_true",
        help="Wrap GeoJSON MultiPolygon in a Feature",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override OSM API base URL (for testing)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def build_service(
    *,
    ewkt: bool = False,
    geojson_feature: bool = False,
    base_url: str | None = None,
) -> RelationGeometryService:
    """Wires concrete collaborators for the CLI.

    Args:
        ewkt: Enable EWKT output for the WKT exporter.
        geojson_feature: Export GeoJSON as a Feature.
        base_url: Optional OSM API base URL override.

    Returns:
        Configured service instance.
    """
    client_kwargs = {}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OsmApiClient(**client_kwargs)

    def fetch_missing(relation_id: int):
        return client.fetch_relation_full(relation_id)

    assembler = RelationAssembler(fetch_missing=fetch_missing)
    simplifier = GeometrySimplifier()
    exporters = {
        "poly": PolyExporter(),
        "geojson": GeoJsonExporter(as_feature=geojson_feature),
        "wkt": WktExporter(ewkt=ewkt),
        "svg": SvgExporter(),
    }
    return RelationGeometryService(
        client=client,
        assembler=assembler,
        simplifier=simplifier,
        exporters=exporters,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    formats = [part.strip() for part in args.formats.split(",") if part.strip()]
    if (
        len(formats) != 1
        and args.output is not None
        and args.output_dir is None
    ):
        parser.error("--output requires a single format (or use --output-dir)")

    service = build_service(
        ewkt=args.ewkt,
        geojson_feature=args.geojson_feature,
        base_url=args.base_url,
    )
    try:
        paths = service.run(
            args.relation_id,
            formats,
            simplify_tolerance=args.simplify,
            output=args.output,
            output_dir=args.output_dir,
        )
    except (OsmClientError, AssemblyError, ValueError, OSError) as error:
        logging.error("%s", error)
        return 1

    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
