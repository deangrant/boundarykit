"""Assemble multipolygon geometry from OSM relation members."""

from __future__ import annotations

from collections.abc import Callable, Sequence
import logging

from osm_geometry import models

_LOG = logging.getLogger(__name__)


class AssemblyError(Exception):
    """Relation geometry could not be assembled from available elements."""


class RelationAssembler:
    """Builds MultiPolygon geometry from an element store."""

    def __init__(
        self,
        fetch_missing: Callable[[int], models.ElementStore] | None = None,
    ) -> None:
        """Creates an assembler.

        Args:
            fetch_missing: Optional callback to fetch additional relation
                stores when a nested relation is absent from the current store.
        """
        self._fetch_missing = fetch_missing

    def assemble(
        self,
        store: models.ElementStore,
        relation_id: int,
    ) -> models.MultiPolygon:
        """Assembles geometry for a relation and nested member relations.

        Args:
            store: Available OSM elements.
            relation_id: Root relation id.

        Returns:
            Assembled multipolygon (may be empty for non-area relations that
            only contribute via children).

        Raises:
            AssemblyError: If the relation is missing from the store.
        """
        return self._assemble_recursive(store, relation_id, seen=set())

    def _assemble_recursive(
        self,
        store: models.ElementStore,
        relation_id: int,
        *,
        seen: set[int],
    ) -> models.MultiPolygon:
        if relation_id in seen:
            _LOG.warning("Skipping cyclic relation reference %s", relation_id)
            return models.MultiPolygon(relation_id=relation_id)
        seen.add(relation_id)

        relation = store.relations.get(relation_id)
        if relation is None and self._fetch_missing is not None:
            store.merge(self._fetch_missing(relation_id))
            relation = store.relations.get(relation_id)
        if relation is None:
            raise AssemblyError(f"Relation {relation_id} not found in store")

        own = self._assemble_own_polygons(store, relation)
        child_geoms: list[models.MultiPolygon] = []
        for member in relation.members:
            if member.member_type != "relation":
                continue
            if member.ref not in store.relations and self._fetch_missing:
                store.merge(self._fetch_missing(member.ref))
            try:
                child = self._assemble_recursive(store, member.ref, seen=seen)
            except AssemblyError as err:
                _LOG.warning(
                    "Could not assemble nested relation %s: %s",
                    member.ref,
                    err,
                )
                continue
            if not child.is_empty():
                child_geoms.append(child)

        polygons = list(own)
        for geom in child_geoms:
            for polygon in geom.polygons:
                polygons.append(polygon)
        return models.MultiPolygon(
            polygons=polygons,
            relation_id=relation_id,
            name=relation.name,
        )

    def _assemble_own_polygons(
        self,
        store: models.ElementStore,
        relation: models.OsmRelation,
    ) -> list[models.Polygon]:
        outer_ways: list[list[models.LatLon]] = []
        inner_ways: list[list[models.LatLon]] = []
        for member in relation.members:
            if member.member_type != "way":
                continue
            way = store.ways.get(member.ref)
            if way is None:
                _LOG.warning(
                    "Missing way %s on relation %s",
                    member.ref,
                    relation.osm_id,
                )
                continue
            line = self._way_coordinates(store, way)
            if len(line) < 2:
                continue
            role = member.role or "outer"
            if role == "inner":
                inner_ways.append(line)
            else:
                # Treat empty/label/outer and unknown area roles as outer.
                outer_ways.append(line)

        outer_rings = _rings_from_ways(outer_ways)
        inner_rings = _rings_from_ways(inner_ways)
        if not outer_rings:
            return []
        return _assign_inners(outer_rings, inner_rings)

    def _way_coordinates(
        self,
        store: models.ElementStore,
        way: models.OsmWay,
    ) -> list[models.LatLon]:
        points: list[models.LatLon] = []
        for node_id in way.node_ids:
            node = store.nodes.get(node_id)
            if node is None:
                _LOG.warning("Missing node %s on way %s", node_id, way.osm_id)
                continue
            points.append(node.coordinate)
        return points


def _rings_from_ways(
    ways: Sequence[list[models.LatLon]],
) -> list[models.Ring]:
    """Chains way polylines into closed rings by matching endpoints."""
    remaining = [list(way) for way in ways if len(way) >= 2]
    rings: list[models.Ring] = []
    while remaining:
        chain = remaining.pop(0)
        progressed = True
        while progressed and not _is_closed_line(chain):
            progressed = False
            start = chain[0]
            end = chain[-1]
            for index, candidate in enumerate(remaining):
                cand_start = candidate[0]
                cand_end = candidate[-1]
                if _same_point(end, cand_start):
                    chain.extend(candidate[1:])
                    remaining.pop(index)
                    progressed = True
                    break
                if _same_point(end, cand_end):
                    chain.extend(reversed(candidate[:-1]))
                    remaining.pop(index)
                    progressed = True
                    break
                if _same_point(start, cand_end):
                    chain = candidate[:-1] + chain
                    remaining.pop(index)
                    progressed = True
                    break
                if _same_point(start, cand_start):
                    chain = list(reversed(candidate[1:])) + chain
                    remaining.pop(index)
                    progressed = True
                    break
        if _is_closed_line(chain) and len(chain) >= 4:
            rings.append(models.Ring(points=chain))
        else:
            _LOG.warning("Could not close ring from %s segments", len(chain))
    return rings


def _assign_inners(
    outers: Sequence[models.Ring],
    inners: Sequence[models.Ring],
) -> list[models.Polygon]:
    polygons = [models.Polygon(outer=outer, inners=[]) for outer in outers]
    for inner in inners:
        if not inner.points:
            continue
        probe = inner.points[0]
        assigned = False
        for polygon in polygons:
            if _point_in_ring(probe, polygon.outer):
                polygon.inners.append(inner)
                assigned = True
                break
        if not assigned and polygons:
            # Fall back to first outer when PIP is inconclusive.
            polygons[0].inners.append(inner)
            _LOG.warning("Assigned inner ring to first outer by fallback")
    return polygons


def _is_closed_line(points: Sequence[models.LatLon]) -> bool:
    return len(points) >= 4 and _same_point(points[0], points[-1])


def _same_point(left: models.LatLon, right: models.LatLon) -> bool:
    return left.lat == right.lat and left.lon == right.lon


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
