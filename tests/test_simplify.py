"""Tests for Douglas–Peucker simplification."""

from __future__ import annotations

import sys
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

    def test_large_ring_does_not_recurse(self) -> None:
        """Iterative DP must handle rings larger than the recursion limit."""
        open_count = sys.getrecursionlimit() + 50
        points = _dense_square_ring(open_count)
        geom = models.MultiPolygon(
            polygons=[models.Polygon(outer=models.Ring(points=points))]
        )
        result = simplify.GeometrySimplifier().simplify(geom, 0.01)
        ring = result.polygons[0].outer
        self.assertTrue(ring.is_closed())
        self.assertGreaterEqual(len(ring.points), 4)
        self.assertLess(len(ring.points), len(points))


def _dense_square_ring(open_vertex_count: int) -> list[models.LatLon]:
    """Builds a closed unit-square ring with many collinear edge samples."""
    per_side = max(open_vertex_count // 4, 2)
    points: list[models.LatLon] = []
    # Bottom: (0,0) -> (0,1), left: (0,1) -> (1,1), top: (1,1) -> (1,0),
    # right: (1,0) -> (0,0) excluding the final closing duplicate until end.
    for i in range(per_side):
        t = i / per_side
        points.append(models.LatLon(0.0, t))
    for i in range(per_side):
        t = i / per_side
        points.append(models.LatLon(t, 1.0))
    for i in range(per_side):
        t = i / per_side
        points.append(models.LatLon(1.0, 1.0 - t))
    for i in range(per_side):
        t = i / per_side
        points.append(models.LatLon(1.0 - t, 0.0))
    points.append(points[0])
    return points


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
