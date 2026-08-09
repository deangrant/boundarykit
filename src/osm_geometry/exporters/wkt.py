"""WKT / EWKT exporter."""

from __future__ import annotations

import pathlib

from osm_geometry import models


class WktExporter:
    """Exports WKT or EWKT multipolygon text."""

    format_id = "wkt"
    file_extension = ".wkt"

    def __init__(self, ewkt: bool = False, srid: int = 4326) -> None:
        self._ewkt = ewkt
        self._srid = srid

    def export(self, geometry: models.MultiPolygon, path: pathlib.Path) -> None:
        """Writes WKT to path.

        Args:
            geometry: Geometry to export.
            path: Destination file path.
        """
        path.write_text(self.dumps(geometry), encoding="utf-8")

    def dumps(self, geometry: models.MultiPolygon) -> str:
        """Returns WKT/EWKT text for geometry."""
        polygons = []
        for polygon in geometry.polygons:
            rings = [_format_ring(polygon.outer)]
            rings.extend(_format_ring(inner) for inner in polygon.inners)
            polygons.append(f'({",".join(rings)})')
        body = f'MULTIPOLYGON({",".join(polygons)})'
        if self._ewkt:
            return f"SRID={self._srid};{body}\n"
        return body + "\n"


def _format_ring(ring: models.Ring) -> str:
    coords = ",".join(f"{point.lon} {point.lat}" for point in ring.points)
    return f"({coords})"
