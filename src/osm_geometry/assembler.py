"""Assemble multipolygon geometry from OSM relation members."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from osm_geometry import models

_WAY_NON_GEOMETRY_ROLES = frozenset(
    {
        "label",
        "admin_centre",
        "label_center",
        "capital",
        "subarea",
    }
)
_RELATION_NON_GEOMETRY_ROLES = frozenset(
    {
        "label",
        "admin_centre",
        "label_center",
        "capital",
    }
)
_INCLUDE_RELATION_ROLES = frozenset({"", "outer", "subarea"})


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
            AssemblyError: If the relation is missing, members are incomplete,
                roles are invalid, rings cannot be chained uniquely, or inners
                cannot be assigned to exactly one outer.
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
            raise AssemblyError(
                f"Cyclic relation reference involving {relation_id}"
            )
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
            role = member.role or ""
            if role in _RELATION_NON_GEOMETRY_ROLES:
                continue
            if role == "inner":
                raise AssemblyError(
                    f"Unsupported nested relation role 'inner' for "
                    f"relation {member.ref} on {relation.osm_id}"
                )
            if role not in _INCLUDE_RELATION_ROLES:
                raise AssemblyError(
                    f"Unknown relation member role {role!r} for "
                    f"relation {member.ref} on {relation.osm_id}"
                )
            if member.ref not in store.relations and self._fetch_missing:
                store.merge(self._fetch_missing(member.ref))
            child = self._assemble_recursive(store, member.ref, seen=seen)
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
            role = member.role or ""
            if role in _WAY_NON_GEOMETRY_ROLES:
                continue
            if role not in ("", "outer", "inner"):
                raise AssemblyError(
                    f"Unknown way member role {role!r} for way "
                    f"{member.ref} on relation {relation.osm_id}"
                )
            way = store.ways.get(member.ref)
            if way is None:
                raise AssemblyError(
                    f"Missing way {member.ref} on relation {relation.osm_id}"
                )
            line = self._way_coordinates(store, way)
            if len(line) < 2:
                raise AssemblyError(
                    f"Way {way.osm_id} has fewer than 2 resolvable nodes"
                )
            if role == "inner":
                inner_ways.append(line)
            else:
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
                raise AssemblyError(
                    f"Missing node {node_id} on way {way.osm_id}"
                )
            points.append(node.coordinate)
        return points


def _rings_from_ways(
    ways: Sequence[list[models.LatLon]],
) -> list[models.Ring]:
    """Chains way polylines into closed rings by matching endpoints.

    More than one match at the same chain endpoint is treated as an
    ambiguous junction. Unclosed chains raise AssemblyError.

    Args:
        ways: Way polylines with at least two points each.

    Returns:
        Closed rings assembled from the ways.

    Raises:
        AssemblyError: If chaining is ambiguous or a ring cannot close.
    """
    remaining = [list(way) for way in ways if len(way) >= 2]
    rings: list[models.Ring] = []
    while remaining:
        chain = remaining.pop(0)
        while not _is_closed_line(chain):
            end_matches = _end_matches(chain, remaining)
            start_matches = _start_matches(chain, remaining)
            if len(end_matches) > 1 or len(start_matches) > 1:
                raise AssemblyError(
                    "Ambiguous way junction: multiple endpoint matches"
                )
            if end_matches:
                index, chain = end_matches[0]
            elif start_matches:
                index, chain = start_matches[0]
            else:
                raise AssemblyError(
                    "Could not close ring: no matching way endpoint"
                )
            remaining.pop(index)
        if len(chain) < 4:
            raise AssemblyError("Closed ring has fewer than 4 vertices")
        rings.append(models.Ring(points=chain))
    return rings


def _end_matches(
    chain: Sequence[models.LatLon],
    remaining: Sequence[Sequence[models.LatLon]],
) -> list[tuple[int, list[models.LatLon]]]:
    """Returns (index, extended_chain) for ways that attach to chain[-1]."""
    end = chain[-1]
    matches: list[tuple[int, list[models.LatLon]]] = []
    for index, candidate in enumerate(remaining):
        if _same_point(end, candidate[0]):
            matches.append((index, list(chain) + list(candidate[1:])))
        elif _same_point(end, candidate[-1]):
            matches.append(
                (index, list(chain) + list(reversed(candidate[:-1])))
            )
    return matches


def _start_matches(
    chain: Sequence[models.LatLon],
    remaining: Sequence[Sequence[models.LatLon]],
) -> list[tuple[int, list[models.LatLon]]]:
    """Returns (index, extended_chain) for ways that attach to chain[0]."""
    start = chain[0]
    matches: list[tuple[int, list[models.LatLon]]] = []
    for index, candidate in enumerate(remaining):
        if _same_point(start, candidate[-1]):
            matches.append((index, list(candidate[:-1]) + list(chain)))
        elif _same_point(start, candidate[0]):
            matches.append((index, list(reversed(candidate[1:])) + list(chain)))
    return matches


def _assign_inners(
    outers: Sequence[models.Ring],
    inners: Sequence[models.Ring],
) -> list[models.Polygon]:
    """Assigns each inner ring to exactly one containing outer.

    Args:
        outers: Outer rings.
        inners: Inner rings to assign by point-in-polygon.

    Returns:
        Polygons with inners attached.

    Raises:
        AssemblyError: If an inner is inside zero or multiple outers.
    """
    polygons = [models.Polygon(outer=outer, inners=[]) for outer in outers]
    for inner in inners:
        if not inner.points:
            raise AssemblyError("Inner ring has no points")
        probe = inner.points[0]
        containing = [
            polygon
            for polygon in polygons
            if _point_in_ring(probe, polygon.outer)
        ]
        if len(containing) != 1:
            raise AssemblyError(
                "Inner ring must be contained by exactly one outer "
                f"(found {len(containing)})"
            )
        containing[0].inners.append(inner)
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
