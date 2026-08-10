"""Shared geometry predicates for rings and points."""

from __future__ import annotations

from boundarykit import models


def point_in_ring(point: models.LatLon, ring: models.Ring) -> bool:
    """Ray-casting point-in-polygon test (lon/lat as x/y).

    Args:
        point: Probe coordinate.
        ring: Closed ring to test against.

    Returns:
        True when the point lies inside the ring.
    """
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
