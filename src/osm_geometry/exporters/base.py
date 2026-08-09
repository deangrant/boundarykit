"""Exporter protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from osm_geometry.models import MultiPolygon


class GeometryExporter(Protocol):
    """Writes a multipolygon to a destination path."""

    format_id: str
    file_extension: str

    def export(self, geometry: MultiPolygon, path: Path) -> None:
        """Writes geometry to path."""
