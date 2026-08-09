"""Orchestrates fetch, assemble, simplify, and export."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import logging
import pathlib
import re

from osm_geometry import assembler
from osm_geometry import client
from osm_geometry import models
from osm_geometry import simplify
from osm_geometry.exporters import base

_LOG = logging.getLogger(__name__)
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class RelationGeometryService:
    """High-level workflow for relation geometry export."""

    def __init__(
        self,
        osm_client: client.OsmApiClientProtocol,
        relation_assembler: assembler.RelationAssembler,
        geometry_simplifier: simplify.GeometrySimplifier,
        exporters: Mapping[str, base.GeometryExporter],
    ) -> None:
        """Creates a service with injected collaborators.

        Args:
            osm_client: Fetches OSM relation payloads.
            relation_assembler: Builds multipolygons from element stores.
            geometry_simplifier: Optional vertex simplification.
            exporters: Format id to exporter implementations.
        """
        self._client = osm_client
        self._assembler = relation_assembler
        self._simplifier = geometry_simplifier
        self._exporters = dict(exporters)

    def build_geometry(
        self,
        relation_id: int,
        simplify_tolerance: float | None = None,
    ) -> models.MultiPolygon:
        """Fetches and assembles geometry for a relation.

        Args:
            relation_id: OSM relation id.
            simplify_tolerance: Optional Douglas–Peucker tolerance in degrees.

        Returns:
            Assembled (and optionally simplified) multipolygon.

        Raises:
            client.OsmClientError: When the API fetch fails.
            assembler.AssemblyError: When geometry cannot be built.
        """
        store = self._client.fetch_relation_full(relation_id)
        geometry = self._assembler.assemble(store, relation_id)
        if geometry.is_empty():
            raise assembler.AssemblyError(
                f"Relation {relation_id} produced no polygon geometry"
            )
        return self._simplifier.simplify(geometry, simplify_tolerance)

    def export(
        self,
        geometry: models.MultiPolygon,
        formats: Sequence[str],
        *,
        output: pathlib.Path | None = None,
        output_dir: pathlib.Path | None = None,
    ) -> list[pathlib.Path]:
        """Exports geometry to one or more formats.

        Args:
            geometry: Geometry to write.
            formats: Exporter format ids.
            output: Single output path (only when one format is requested).
            output_dir: Directory for multi-format output.

        Returns:
            List of written paths.

        Raises:
            ValueError: On unknown format or invalid path combination.
        """
        normalized = [fmt.strip().lower() for fmt in formats if fmt.strip()]
        if not normalized:
            raise ValueError("At least one export format is required")

        unknown = [fmt for fmt in normalized if fmt not in self._exporters]
        if unknown:
            raise ValueError(f'Unknown export format(s): {", ".join(unknown)}')

        if len(normalized) == 1 and output is not None:
            exporter = self._exporters[normalized[0]]
            path = output
            path.parent.mkdir(parents=True, exist_ok=True)
            exporter.export(geometry, path)
            _LOG.info("Wrote %s", path)
            return [path]

        directory = output_dir or pathlib.Path.cwd()
        directory.mkdir(parents=True, exist_ok=True)
        stem = geometry.name or (
            f"relation_{geometry.relation_id}"
            if geometry.relation_id is not None
            else "geometry"
        )
        safe_stem = _safe_filename(stem)
        written: list[pathlib.Path] = []
        for fmt in normalized:
            exporter = self._exporters[fmt]
            path = directory / f"{safe_stem}{exporter.file_extension}"
            exporter.export(geometry, path)
            _LOG.info("Wrote %s", path)
            written.append(path)
        return written

    def run(
        self,
        relation_id: int,
        formats: Iterable[str],
        *,
        simplify_tolerance: float | None = None,
        output: pathlib.Path | None = None,
        output_dir: pathlib.Path | None = None,
    ) -> list[pathlib.Path]:
        """Builds geometry and exports it.

        Args:
            relation_id: OSM relation id.
            formats: Export format ids.
            simplify_tolerance: Optional simplify tolerance.
            output: Optional single-file output path.
            output_dir: Optional multi-format output directory.

        Returns:
            Written file paths.

        Raises:
            client.OsmClientError: When the API fetch fails.
            assembler.AssemblyError: When geometry cannot be built.
            ValueError: On unknown format or invalid path combination.
        """
        geometry = self.build_geometry(
            relation_id,
            simplify_tolerance=simplify_tolerance,
        )
        return self.export(
            geometry,
            list(formats),
            output=output,
            output_dir=output_dir,
        )


def _safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", name).strip("._")
    return (cleaned or "geometry")[:120]
