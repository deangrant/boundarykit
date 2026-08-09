"""GeoJSON exporter."""

from __future__ import annotations

import json
import pathlib
from typing import Any

from osm_geometry import models


class GeoJsonExporter:
    """Exports GeoJSON MultiPolygon geometry or Feature."""

    format_id = "geojson"
    file_extension = ".geojson"

    def __init__(self, as_feature: bool = False) -> None:
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
        coordinates = []
        for polygon in geometry.polygons:
            rings = [_ring_coords(polygon.outer)]
            rings.extend(_ring_coords(inner) for inner in polygon.inners)
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


def _ring_coords(ring: models.Ring) -> list[list[float]]:
    return [[point.lon, point.lat] for point in ring.points]
