"""Osmosis .poly exporter."""

from __future__ import annotations

import pathlib

from osm_geometry import models


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
        name = geometry.name or (
            f"relation_{geometry.relation_id}"
            if geometry.relation_id is not None
            else "polygon"
        )
        lines = [name]
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
