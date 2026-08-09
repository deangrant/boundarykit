"""Geometry simplification helpers."""

from __future__ import annotations

import dataclasses
import math

from osm_geometry import models

_METERS_PER_DEGREE = 111_320.0


@dataclasses.dataclass(frozen=True, slots=True)
class _XY:
    """Projected planar coordinates in meters."""

    x: float
    y: float


class GeometrySimplifier:
    """Simplifies multipolygon rings with meter-space Douglas–Peucker."""

    def simplify(
        self,
        geometry: models.MultiPolygon,
        tolerance: float | None,
    ) -> models.MultiPolygon:
        """Returns a simplified copy, or the input when tolerance is unused.

        Args:
            geometry: Source multipolygon.
            tolerance: Maximum perpendicular distance in meters under a
                local equirectangular projection. None or values <= 0 leave
                geometry unchanged.

        Returns:
            Simplified multipolygon (new instance when changed). Rings that
            would become topologically invalid are left unchanged.
        """
        if tolerance is None or tolerance <= 0:
            return geometry
        polygons = [
            self._simplify_polygon(polygon, tolerance)
            for polygon in geometry.polygons
        ]
        return models.MultiPolygon(
            polygons=polygons,
            relation_id=geometry.relation_id,
            name=geometry.name,
        )

    def _simplify_polygon(
        self,
        polygon: models.Polygon,
        tolerance: float,
    ) -> models.Polygon:
        outer = self._simplify_ring(polygon.outer, tolerance)
        inners: list[models.Ring] = []
        for inner in polygon.inners:
            candidate = self._simplify_ring(inner, tolerance)
            if candidate.points and _point_in_ring(candidate.points[0], outer):
                inners.append(candidate)
            else:
                inners.append(inner)
        return models.Polygon(outer=outer, inners=inners)

    def _simplify_ring(
        self, ring: models.Ring, tolerance: float
    ) -> models.Ring:
        points = list(ring.points)
        if len(points) < 4:
            return models.Ring(points=points)
        closed = (
            points[0].lat == points[-1].lat and points[0].lon == points[-1].lon
        )
        work = points[:-1] if closed else points
        if len(work) < 3:
            return ring

        projected = _project_meters(work)
        keep_indices = _douglas_peucker_indices(projected, tolerance)
        simplified = [work[i] for i in keep_indices]
        if len(simplified) < 3:
            return ring
        if closed:
            simplified = [*simplified, simplified[0]]
        candidate = models.Ring(points=simplified)
        if not _is_valid_ring(candidate):
            return ring
        return candidate


def _project_meters(points: list[models.LatLon]) -> list[_XY]:
    """Projects WGS84 points to local equirectangular meters."""
    lat0 = sum(point.lat for point in points) / len(points)
    lon0 = sum(point.lon for point in points) / len(points)
    cos_lat = math.cos(math.radians(lat0))
    projected: list[_XY] = []
    for point in points:
        x = (point.lon - lon0) * cos_lat * _METERS_PER_DEGREE
        y = (point.lat - lat0) * _METERS_PER_DEGREE
        projected.append(_XY(x=x, y=y))
    return projected


def _douglas_peucker_indices(points: list[_XY], tolerance: float) -> list[int]:
    """Returns ascending indices kept by iterative Douglas–Peucker.

    Args:
        points: Open polyline in planar meters.
        tolerance: Maximum perpendicular distance in meters.

    Returns:
        Sorted vertex indices to retain.
    """
    if len(points) < 3:
        return list(range(len(points)))

    keep = [False] * len(points)
    keep[0] = True
    keep[-1] = True
    stack: list[tuple[int, int]] = [(0, len(points) - 1)]

    while stack:
        start_idx, end_idx = stack.pop()
        start = points[start_idx]
        end = points[end_idx]
        max_distance = -1.0
        index = start_idx
        for i in range(start_idx + 1, end_idx):
            distance = _perpendicular_distance(points[i], start, end)
            if distance > max_distance:
                index = i
                max_distance = distance
        if max_distance > tolerance:
            keep[index] = True
            stack.append((start_idx, index))
            stack.append((index, end_idx))

    return [i for i, retained in enumerate(keep) if retained]


def _perpendicular_distance(point: _XY, start: _XY, end: _XY) -> float:
    """Returns perpendicular distance from point to segment in meters."""
    dx = end.x - start.x
    dy = end.y - start.y
    if dx == 0 and dy == 0:
        return ((point.x - start.x) ** 2 + (point.y - start.y) ** 2) ** 0.5
    t = ((point.x - start.x) * dx + (point.y - start.y) * dy) / (
        dx * dx + dy * dy
    )
    t = max(0.0, min(1.0, t))
    proj_x = start.x + t * dx
    proj_y = start.y + t * dy
    return ((point.x - proj_x) ** 2 + (point.y - proj_y) ** 2) ** 0.5


def _is_valid_ring(ring: models.Ring) -> bool:
    """Returns True when ring is closed, large enough, and simple."""
    if not ring.is_closed() or len(ring.points) < 4:
        return False
    return not _ring_self_intersects(ring)


def _ring_self_intersects(ring: models.Ring) -> bool:
    """Returns True when a closed ring has crossing non-adjacent edges."""
    pts = ring.points
    # Last point duplicates the first for a closed ring.
    n = len(pts) - 1
    if n < 4:
        return False
    for i in range(n):
        a1 = pts[i]
        a2 = pts[(i + 1) % n]
        for j in range(i + 1, n):
            # Skip adjacent edges and the closing edge pair (0, n-1).
            if abs(i - j) <= 1:
                continue
            if i == 0 and j == n - 1:
                continue
            b1 = pts[j]
            b2 = pts[(j + 1) % n]
            if _segments_intersect(a1, a2, b1, b2):
                return True
    return False


def _segments_intersect(
    a1: models.LatLon,
    a2: models.LatLon,
    b1: models.LatLon,
    b2: models.LatLon,
) -> bool:
    """Proper intersection of open segments in lon/lat plane (topology)."""
    o1 = _orient(a1, a2, b1)
    o2 = _orient(a1, a2, b2)
    o3 = _orient(b1, b2, a1)
    o4 = _orient(b1, b2, a2)
    if o1 == 0 or o2 == 0 or o3 == 0 or o4 == 0:
        # Treat touching/collinear as non-crossing for simplification guards.
        return False
    return o1 != o2 and o3 != o4


def _orient(a: models.LatLon, b: models.LatLon, c: models.LatLon) -> int:
    """Returns 1/0/-1 for left/on/right turn using lon as x and lat as y."""
    value = (b.lon - a.lon) * (c.lat - a.lat) - (b.lat - a.lat) * (
        c.lon - a.lon
    )
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _point_in_ring(point: models.LatLon, ring: models.Ring) -> bool:
    """Ray-casting point-in-polygon test (lon/lat as x/y)."""
    x = point.lon
    y = point.lat
    inside = False
    pts = ring.points
    j = len(pts) - 1
    for i, pi in enumerate(pts):
        pj = pts[j]
        intersects = ((pi.lat > y) != (pj.lat > y)) and (
            x
            < (pj.lon - pi.lon) * (y - pi.lat) / (pj.lat - pi.lat + 0.0)
            + pi.lon
        )
        if intersects:
            inside = not inside
        j = i
    return inside
