"""GeoJSON exporter."""

from __future__ import annotations

import json
import pathlib
from typing import Any, ClassVar

from boundarykit import models


class GeoJsonExporter:
    """Exports GeoJSON MultiPolygon geometry or Feature."""

    format_id: ClassVar[str] = "geojson"
    file_extension: ClassVar[str] = ".geojson"

    def __init__(self, as_feature: bool = False) -> None:
        """Creates a GeoJSON exporter.

        Args:
            as_feature: When True, wrap geometry in a Feature with name
                properties.
        """
        self._as_feature = as_feature

    def export(self, geometry: models.MultiPolygon, path: pathlib.Path) -> None:
        """Writes GeoJSON to path.

        Args:
            geometry: Geometry to export.
            path: Destination file path.
        """
        path.write_text(self.dumps(geometry), encoding="utf-8")

    def dumps(self, geometry: models.MultiPolygon) -> str:
        """Returns GeoJSON text for geometry."""
        payload = self._build(geometry)
        return json.dumps(payload, indent=2) + "\n"

    def _build(self, geometry: models.MultiPolygon) -> dict[str, Any]:
        coordinates: list[list[list[list[float]]]] = []
        for polygon in geometry.polygons:
            rings = [_oriented_ring(polygon.outer, clockwise=False)]
            rings.extend(
                _oriented_ring(inner, clockwise=True)
                for inner in polygon.inners
            )
            coordinates.append(rings)
        geom_obj: dict[str, Any] = {
            "type": "MultiPolygon",
            "coordinates": coordinates,
        }
        if not self._as_feature:
            return geom_obj
        properties: dict[str, Any] = {}
        if geometry.relation_id is not None:
            properties["osm_relation_id"] = geometry.relation_id
        if geometry.name:
            properties["name"] = geometry.name
        return {
            "type": "Feature",
            "properties": properties,
            "geometry": geom_obj,
        }


def _signed_area(ring: models.Ring) -> float:
    """Returns shoelace signed area (lon=x, lat=y); positive is CCW."""
    pts = ring.points
    if len(pts) < 2:
        return 0.0
    total = 0.0
    for index in range(len(pts) - 1):
        x1 = pts[index].lon
        y1 = pts[index].lat
        x2 = pts[index + 1].lon
        y2 = pts[index + 1].lat
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _oriented_ring(ring: models.Ring, *, clockwise: bool) -> list[list[float]]:
    """Returns [lon, lat] coords with RFC 7946 winding.

    Args:
        ring: Closed ring to export.
        clockwise: True for holes (CW), False for exteriors (CCW).
    """
    points = list(ring.points)
    area = _signed_area(ring)
    is_clockwise = area < 0.0
    if clockwise != is_clockwise and area != 0.0:
        points = list(reversed(points))
    return [[point.lon, point.lat] for point in points]
