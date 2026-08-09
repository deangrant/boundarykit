"""Exporter protocol."""

from __future__ import annotations

import pathlib
from typing import Protocol

from boundarykit import models


class GeometryExporter(Protocol):
    """Writes a multipolygon to a destination path."""

    format_id: str
    file_extension: str

    def export(self, geometry: models.MultiPolygon, path: pathlib.Path) -> None:
        """Writes geometry to path."""
