"""Geometry simplification helpers."""

from __future__ import annotations

from osm_geometry import models


class GeometrySimplifier:
    """Simplifies multipolygon rings with Douglas–Peucker."""

    def simplify(
        self,
        geometry: models.MultiPolygon,
        tolerance: float | None,
    ) -> models.MultiPolygon:
        """Returns a simplified copy, or the input when tolerance is unused.

        Args:
            geometry: Source multipolygon.
            tolerance: Maximum perpendicular distance in degrees. None or
                values <= 0 leave geometry unchanged.

        Returns:
            Simplified multipolygon (new instance when changed).
        """
        if tolerance is None or tolerance <= 0:
            return geometry
        polygons = [
            models.Polygon(
                outer=self._simplify_ring(polygon.outer, tolerance),
                inners=[
                    self._simplify_ring(inner, tolerance)
                    for inner in polygon.inners
                ],
            )
            for polygon in geometry.polygons
        ]
        return models.MultiPolygon(
            polygons=polygons,
            relation_id=geometry.relation_id,
            name=geometry.name,
        )

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
        simplified = _douglas_peucker(work, tolerance)
        if len(simplified) < 3:
            return ring
        if closed:
            simplified = [*simplified, simplified[0]]
        return models.Ring(points=simplified)


def _douglas_peucker(
    points: list[models.LatLon], tolerance: float
) -> list[models.LatLon]:
    """Simplifies a polyline with iterative Douglas–Peucker.

    Uses an explicit stack of index ranges so large rings cannot raise
    RecursionError.

    Args:
        points: Open polyline (first != last for closed rings).
        tolerance: Maximum perpendicular distance in degrees.

    Returns:
        Simplified polyline preserving original endpoint order.
    """
    if len(points) < 3:
        return list(points)

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

    return [point for point, retained in zip(points, keep) if retained]


def _perpendicular_distance(
    point: models.LatLon,
    start: models.LatLon,
    end: models.LatLon,
) -> float:
    """Returns perpendicular distance from point to segment in degree space."""
    dx = end.lon - start.lon
    dy = end.lat - start.lat
    if dx == 0 and dy == 0:
        return (
            (point.lon - start.lon) ** 2 + (point.lat - start.lat) ** 2
        ) ** 0.5
    t = ((point.lon - start.lon) * dx + (point.lat - start.lat) * dy) / (
        dx * dx + dy * dy
    )
    t = max(0.0, min(1.0, t))
    proj_lon = start.lon + t * dx
    proj_lat = start.lat + t * dy
    return ((point.lon - proj_lon) ** 2 + (point.lat - proj_lat) ** 2) ** 0.5
