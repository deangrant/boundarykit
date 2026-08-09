"""Osmosis .poly exporter."""

from __future__ import annotations

import pathlib
import re

from osm_geometry import models

_WHITESPACE = re.compile(r"\s+")


class PolyExporter:
    """Exports Osmosis-compatible .poly text."""

    format_id = "poly"
    file_extension = ".poly"

    def export(self, geometry: models.MultiPolygon, path: pathlib.Path) -> None:
        """Writes .poly content to path.

        Args:
            geometry: Geometry to export.
            path: Destination file path.
        """
        path.write_text(self.dumps(geometry), encoding="utf-8")

    def dumps(self, geometry: models.MultiPolygon) -> str:
        """Returns .poly text for geometry."""
        lines = [_poly_name(geometry)]
        ring_index = 1
        for polygon in geometry.polygons:
            lines.append(str(ring_index))
            ring_index += 1
            for point in polygon.outer.points:
                lines.append(f"  {point.lon}  {point.lat}")
            lines.append("END")
            for inner in polygon.inners:
                lines.append(f"!{ring_index}")
                ring_index += 1
                for point in inner.points:
                    lines.append(f"  {point.lon}  {point.lat}")
                lines.append("END")
        lines.append("END")
        return "\n".join(lines) + "\n"


def _poly_name(geometry: models.MultiPolygon) -> str:
    """Returns a single-line .poly header name safe for Osmosis parsers."""
    fallback = (
        f"relation_{geometry.relation_id}"
        if geometry.relation_id is not None
        else "polygon"
    )
    raw = geometry.name if geometry.name is not None else fallback
    cleaned = _WHITESPACE.sub(" ", raw).strip()
    if not cleaned or cleaned.upper() == "END" or cleaned.startswith("!"):
        return fallback
    return cleaned
