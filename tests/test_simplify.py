"""Tests for Douglas–Peucker simplification."""

from __future__ import annotations

import sys
import unittest
from unittest import mock

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
        # ~22 km: removes mid-edge vertices on a ~111 km unit square.
        result = simplify.GeometrySimplifier().simplify(geom, 22_000.0)
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
        result = simplify.GeometrySimplifier().simplify(geom, 1_000.0)
        ring = result.polygons[0].outer
        self.assertTrue(ring.is_closed())
        self.assertGreaterEqual(len(ring.points), 4)
        self.assertLess(len(ring.points), len(points))

    def test_meter_space_treats_ew_wiggles_by_latitude(self) -> None:
        """Same degree EW wiggles shrink in meters at high latitude."""
        # East-west corridors with identical degree amplitude: at 70N the
        # meter amplitude is much smaller, so the same meter tolerance
        # removes more vertices than at the equator.
        eq_points = _corridor_with_wiggles(
            base_lat=0.0,
            base_lon=0.0,
            eastward=True,
            amplitude_deg=0.05,
        )
        polar_points = _corridor_with_wiggles(
            base_lat=70.0,
            base_lon=0.0,
            eastward=True,
            amplitude_deg=0.05,
        )
        tolerance_m = 3_000.0
        simplifier = simplify.GeometrySimplifier()
        eq_ew = simplifier.simplify(_ring_geom(eq_points), tolerance_m)
        polar_ew = simplifier.simplify(_ring_geom(polar_points), tolerance_m)
        self.assertLess(
            len(polar_ew.polygons[0].outer.points),
            len(eq_ew.polygons[0].outer.points),
        )

    def test_inner_outside_simplified_outer_keeps_original_inner(
        self,
    ) -> None:
        outer = models.Ring(
            points=[
                models.LatLon(0, 0),
                models.LatLon(0, 2),
                models.LatLon(2, 2),
                models.LatLon(2, 0),
                models.LatLon(0, 0),
            ]
        )
        inner = models.Ring(
            points=[
                models.LatLon(0.5, 0.5),
                models.LatLon(0.5, 1.0),
                models.LatLon(1.0, 1.0),
                models.LatLon(1.0, 0.5),
                models.LatLon(0.5, 0.5),
            ]
        )
        geom = models.MultiPolygon(
            polygons=[models.Polygon(outer=outer, inners=[inner])]
        )
        # Outer collapses away from the inner; guard must keep original inner.
        small_outer = models.Ring(
            points=[
                models.LatLon(1.5, 1.5),
                models.LatLon(1.5, 2.0),
                models.LatLon(2.0, 2.0),
                models.LatLon(2.0, 1.5),
                models.LatLon(1.5, 1.5),
            ]
        )

        def fake_simplify_ring(
            self: simplify.GeometrySimplifier,
            ring: models.Ring,
            tolerance: float,
        ) -> models.Ring:
            del self, tolerance  # Unused.
            if ring is outer or ring.points == outer.points:
                return small_outer
            return ring

        with mock.patch.object(
            simplify.GeometrySimplifier,
            "_simplify_ring",
            fake_simplify_ring,
        ):
            result = simplify.GeometrySimplifier().simplify(geom, 100.0)
        self.assertEqual(result.polygons[0].inners[0].points, inner.points)

    def test_self_intersecting_ring_is_detected(self) -> None:
        bowtie = models.Ring(
            points=[
                models.LatLon(0, 0),
                models.LatLon(1, 1),
                models.LatLon(0, 1),
                models.LatLon(1, 0),
                models.LatLon(0, 0),
            ]
        )
        # pylint: disable-next=protected-access
        self.assertTrue(simplify._ring_self_intersects(bowtie))

    def test_self_intersecting_simplification_keeps_original(self) -> None:
        # Source ring is simple; mocked DP keep-set forms a bowtie.
        points = [
            models.LatLon(0, 0),
            models.LatLon(0.5, 0.25),
            models.LatLon(1, 1),
            models.LatLon(0.5, 0.75),
            models.LatLon(0, 1),
            models.LatLon(0.5, 0.5),
            models.LatLon(1, 0),
            models.LatLon(0, 0),
        ]
        ring = models.Ring(points=points)
        geom = _ring_geom(points)

        def fake_indices(
            projected: list[object], tolerance: float
        ) -> list[int]:
            del projected, tolerance  # Unused.
            # Open-ring indices for (0,0), (1,1), (0,1), (1,0).
            return [0, 2, 4, 6]

        with mock.patch.object(
            simplify, "_douglas_peucker_indices", fake_indices
        ):
            result = simplify.GeometrySimplifier().simplify(geom, 100.0)
        self.assertEqual(result.polygons[0].outer.points, ring.points)


def _ring_geom(points: list[models.LatLon]) -> models.MultiPolygon:
    return models.MultiPolygon(
        polygons=[models.Polygon(outer=models.Ring(points=points))]
    )


def _corridor_with_wiggles(
    *,
    base_lat: float,
    base_lon: float,
    eastward: bool,
    amplitude_deg: float,
) -> list[models.LatLon]:
    """Closed thin rectangle with alternating wiggles on the long edges."""
    length = 1.0
    width = 0.2
    steps = 20
    points: list[models.LatLon] = []
    if eastward:
        for i in range(steps + 1):
            t = i / steps
            lon = base_lon + t * length
            lat = base_lat + (amplitude_deg if i % 2 else 0.0)
            points.append(models.LatLon(lat, lon))
        for i in range(steps + 1):
            t = i / steps
            lon = base_lon + length - t * length
            lat = base_lat + width + (amplitude_deg if i % 2 else 0.0)
            points.append(models.LatLon(lat, lon))
    else:
        for i in range(steps + 1):
            t = i / steps
            lat = base_lat + t * length
            lon = base_lon + (amplitude_deg if i % 2 else 0.0)
            points.append(models.LatLon(lat, lon))
        for i in range(steps + 1):
            t = i / steps
            lat = base_lat + length - t * length
            lon = base_lon + width + (amplitude_deg if i % 2 else 0.0)
            points.append(models.LatLon(lat, lon))
    points.append(points[0])
    return points


def _dense_square_ring(open_vertex_count: int) -> list[models.LatLon]:
    """Builds a closed unit-square ring with many collinear edge samples."""
    per_side = max(open_vertex_count // 4, 2)
    points: list[models.LatLon] = []
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
