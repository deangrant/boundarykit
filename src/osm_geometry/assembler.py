"""Assemble multipolygon geometry from OSM relation members."""

from __future__ import annotations

from collections.abc import Callable, Sequence
import logging

from osm_geometry.models import ElementStore
from osm_geometry.models import LatLon
from osm_geometry.models import MultiPolygon
from osm_geometry.models import OsmRelation
from osm_geometry.models import OsmWay
from osm_geometry.models import Polygon
from osm_geometry.models import Ring

_LOG = logging.getLogger(__name__)


class AssemblyError(Exception):
    """Raised when relation geometry cannot be assembled."""


class RelationAssembler:
    """Builds MultiPolygon geometry from an element store."""

    def __init__(
        self,
        fetch_missing: Callable[[int], ElementStore] | None = None,
    ) -> None:
        """Creates an assembler.

        Args:
            fetch_missing: Optional callback to fetch additional relation
                stores when a nested relation is absent from the current store.
        """
        self._fetch_missing = fetch_missing

    def assemble(
        self,
        store: ElementStore,
        relation_id: int,
        *,
        _seen: set[int] | None = None,
    ) -> MultiPolygon:
        """Assembles geometry for a relation and nested member relations.

        Args:
            store: Available OSM elements.
            relation_id: Root relation id.
            _seen: Internal recursion guard.

        Returns:
            Assembled multipolygon (may be empty for non-area relations that
            only contribute via children).

        Raises:
            AssemblyError: If the relation is missing or yields no geometry
                when one is required at the root.
        """
        seen = _seen if _seen is not None else set()
        if relation_id in seen:
            _LOG.warning("Skipping cyclic relation reference %s", relation_id)
            return MultiPolygon(relation_id=relation_id)
        seen.add(relation_id)

        relation = store.relations.get(relation_id)
        if relation is None and self._fetch_missing is not None:
            store.merge(self._fetch_missing(relation_id))
            relation = store.relations.get(relation_id)
        if relation is None:
            raise AssemblyError(f"Relation {relation_id} not found in store")

        own = self._assemble_own_polygons(store, relation)
        child_geoms: list[MultiPolygon] = []
        for member in relation.members:
            if member.member_type != "relation":
                continue
            child_store = store
            if member.ref not in store.relations and self._fetch_missing:
                store.merge(self._fetch_missing(member.ref))
            try:
                child = self.assemble(child_store, member.ref, _seen=seen)
            except AssemblyError as error:
                _LOG.warning(
                    "Could not assemble nested relation %s: %s",
                    member.ref,
                    error,
                )
                continue
            if not child.is_empty():
                child_geoms.append(child)

        polygons = [*own, *[p for g in child_geoms for p in g.polygons]]
        return MultiPolygon(
            polygons=polygons,
            relation_id=relation_id,
            name=relation.name,
        )

    def _assemble_own_polygons(
        self,
        store: ElementStore,
        relation: OsmRelation,
    ) -> list[Polygon]:
        outer_ways: list[list[LatLon]] = []
        inner_ways: list[list[LatLon]] = []
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
        store: ElementStore,
        way: OsmWay,
    ) -> list[LatLon]:
        points: list[LatLon] = []
        for node_id in way.node_ids:
            node = store.nodes.get(node_id)
            if node is None:
                _LOG.warning("Missing node %s on way %s", node_id, way.osm_id)
                continue
            points.append(node.coordinate)
        return points


def _rings_from_ways(ways: Sequence[list[LatLon]]) -> list[Ring]:
    """Chains way polylines into closed rings by matching endpoints."""
    remaining = [list(way) for way in ways if len(way) >= 2]
    rings: list[Ring] = []
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
            rings.append(Ring(points=chain))
        else:
            _LOG.warning("Could not close ring from %s segments", len(chain))
    return rings


def _assign_inners(
    outers: Sequence[Ring],
    inners: Sequence[Ring],
) -> list[Polygon]:
    polygons = [Polygon(outer=outer, inners=[]) for outer in outers]
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


def _is_closed_line(points: Sequence[LatLon]) -> bool:
    return len(points) >= 4 and _same_point(points[0], points[-1])


def _same_point(left: LatLon, right: LatLon) -> bool:
    return left.lat == right.lat and left.lon == right.lon


def _point_in_ring(point: LatLon, ring: Ring) -> bool:
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
