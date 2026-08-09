"""Tests for Douglas–Peucker simplification."""

from __future__ import annotations

import unittest

from osm_geometry.models import LatLon
from osm_geometry.models import MultiPolygon
from osm_geometry.models import Polygon
from osm_geometry.models import Ring
from osm_geometry.simplify import GeometrySimplifier


class GeometrySimplifierTest(unittest.TestCase):
    """Tests GeometrySimplifier."""

    def test_noop_when_tolerance_none(self) -> None:
        geom = _square()
        result = GeometrySimplifier().simplify(geom, None)
        self.assertIs(result, geom)

    def test_reduces_vertices_and_keeps_closed(self) -> None:
        points = [
            LatLon(0, 0),
            LatLon(0, 0.5),
            LatLon(0, 1),
            LatLon(0.5, 1),
            LatLon(1, 1),
            LatLon(1, 0.5),
            LatLon(1, 0),
            LatLon(0.5, 0),
            LatLon(0, 0),
        ]
        geom = MultiPolygon(polygons=[Polygon(outer=Ring(points=points))])
        result = GeometrySimplifier().simplify(geom, 0.2)
        ring = result.polygons[0].outer
        self.assertTrue(ring.is_closed())
        self.assertLess(len(ring.points), len(points))
        self.assertGreaterEqual(len(ring.points), 4)


def _square() -> MultiPolygon:
    points = [
        LatLon(0, 0),
        LatLon(0, 1),
        LatLon(1, 1),
        LatLon(1, 0),
        LatLon(0, 0),
    ]
    return MultiPolygon(polygons=[Polygon(outer=Ring(points=points))])


if __name__ == "__main__":
    unittest.main()
