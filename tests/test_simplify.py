"""Tests for Douglas–Peucker simplification."""

from __future__ import annotations

import unittest

from osm_geometry import models
from osm_geometry import simplify


class GeometrySimplifierTest(unittest.TestCase):
    """Tests GeometrySimplifier."""

    def test_noop_when_tolerance_none(self) -> None:
        geom = _square()
        result = simplify.GeometrySimplifier().simplify(geom, None)
        self.assertIs(result, geom)

    def test_reduces_vertices_and_keeps_closed(self) -> None:
        points = [
            models.LatLon(0, 0),
            models.LatLon(0, 0.5),
            models.LatLon(0, 1),
            models.LatLon(0.5, 1),
            models.LatLon(1, 1),
            models.LatLon(1, 0.5),
            models.LatLon(1, 0),
            models.LatLon(0.5, 0),
            models.LatLon(0, 0),
        ]
        geom = models.MultiPolygon(
            polygons=[models.Polygon(outer=models.Ring(points=points))]
        )
        result = simplify.GeometrySimplifier().simplify(geom, 0.2)
        ring = result.polygons[0].outer
        self.assertTrue(ring.is_closed())
        self.assertLess(len(ring.points), len(points))
        self.assertGreaterEqual(len(ring.points), 4)


def _square() -> models.MultiPolygon:
    points = [
        models.LatLon(0, 0),
        models.LatLon(0, 1),
        models.LatLon(1, 1),
        models.LatLon(1, 0),
        models.LatLon(0, 0),
    ]
    return models.MultiPolygon(
        polygons=[models.Polygon(outer=models.Ring(points=points))]
    )


if __name__ == "__main__":
    unittest.main()
