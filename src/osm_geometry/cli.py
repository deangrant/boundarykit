"""Command-line interface for osm-geometry."""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys

from osm_geometry import assembler
from osm_geometry import client
from osm_geometry import models
from osm_geometry import service
from osm_geometry import simplify
from osm_geometry.exporters import geojson
from osm_geometry.exporters import poly
from osm_geometry.exporters import svg
from osm_geometry.exporters import wkt


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
        type=pathlib.Path,
        help="Output file when exporting a single format",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
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
) -> service.RelationGeometryService:
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
    osm_client = client.OsmApiClient(**client_kwargs)

    def fetch_missing(relation_id: int) -> models.ElementStore:
        return osm_client.fetch_relation_full(relation_id)

    relation_assembler = assembler.RelationAssembler(
        fetch_missing=fetch_missing
    )
    geometry_simplifier = simplify.GeometrySimplifier()
    exporter_list = [
        poly.PolyExporter(),
        geojson.GeoJsonExporter(as_feature=geojson_feature),
        wkt.WktExporter(ewkt=ewkt),
        svg.SvgExporter(),
    ]
    exporters = {exporter.format_id: exporter for exporter in exporter_list}
    return service.RelationGeometryService(
        osm_client=osm_client,
        relation_assembler=relation_assembler,
        geometry_simplifier=geometry_simplifier,
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

    geometry_service = build_service(
        ewkt=args.ewkt,
        geojson_feature=args.geojson_feature,
        base_url=args.base_url,
    )
    try:
        paths = geometry_service.run(
            args.relation_id,
            formats,
            simplify_tolerance=args.simplify,
            output=args.output,
            output_dir=args.output_dir,
        )
    except (
        client.OsmClientError,
        assembler.AssemblyError,
        ValueError,
        OSError,
    ) as err:
        logging.error("%s", err)
        return 1

    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
