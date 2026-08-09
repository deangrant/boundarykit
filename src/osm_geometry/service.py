"""Orchestrates fetch, assemble, simplify, and export."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import logging
from pathlib import Path
import re

from osm_geometry.assembler import AssemblyError
from osm_geometry.assembler import RelationAssembler
from osm_geometry.client import OsmApiClientProtocol
from osm_geometry.exporters.base import GeometryExporter
from osm_geometry.models import MultiPolygon
from osm_geometry.simplify import GeometrySimplifier

_LOG = logging.getLogger(__name__)
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class RelationGeometryService:
    """High-level workflow for relation geometry export."""

    def __init__(
        self,
        client: OsmApiClientProtocol,
        assembler: RelationAssembler,
        simplifier: GeometrySimplifier,
        exporters: Mapping[str, GeometryExporter],
    ) -> None:
        self._client = client
        self._assembler = assembler
        self._simplifier = simplifier
        self._exporters = dict(exporters)

    def build_geometry(
        self,
        relation_id: int,
        simplify_tolerance: float | None = None,
    ) -> MultiPolygon:
        """Fetches and assembles geometry for a relation.

        Args:
            relation_id: OSM relation id.
            simplify_tolerance: Optional Douglas–Peucker tolerance in degrees.

        Returns:
            Assembled (and optionally simplified) multipolygon.

        Raises:
            AssemblyError: When geometry cannot be built.
        """
        store = self._client.fetch_relation_full(relation_id)
        geometry = self._assembler.assemble(store, relation_id)
        if geometry.is_empty():
            raise AssemblyError(
                f"Relation {relation_id} produced no polygon geometry"
            )
        return self._simplifier.simplify(geometry, simplify_tolerance)

    def export(
        self,
        geometry: MultiPolygon,
        formats: Sequence[str],
        *,
        output: Path | None = None,
        output_dir: Path | None = None,
    ) -> list[Path]:
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

        directory = output_dir or Path.cwd()
        directory.mkdir(parents=True, exist_ok=True)
        stem = geometry.name or (
            f"relation_{geometry.relation_id}"
            if geometry.relation_id is not None
            else "geometry"
        )
        safe_stem = _safe_filename(stem)
        written: list[Path] = []
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
        output: Path | None = None,
        output_dir: Path | None = None,
    ) -> list[Path]:
        """Builds geometry and exports it.

        Args:
            relation_id: OSM relation id.
            formats: Export format ids.
            simplify_tolerance: Optional simplify tolerance.
            output: Optional single-file output path.
            output_dir: Optional multi-format output directory.

        Returns:
            Written file paths.
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
