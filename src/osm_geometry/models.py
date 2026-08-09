"""Domain types for OSM elements and polygon geometry."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass(frozen=True, slots=True)
class LatLon:
    """A geographic coordinate (WGS84)."""

    lat: float
    lon: float


@dataclass(slots=True)
class OsmNode:
    """An OSM node element."""

    osm_id: int
    coordinate: LatLon


@dataclass(slots=True)
class OsmWay:
    """An OSM way element."""

    osm_id: int
    node_ids: list[int] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class OsmMember:
    """A member reference on an OSM relation."""

    member_type: str
    ref: int
    role: str


@dataclass(slots=True)
class OsmRelation:
    """An OSM relation element."""

    osm_id: int
    members: list[OsmMember] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str | None:
        """Returns the relation name tag if present."""
        return self.tags.get("name")


@dataclass(slots=True)
class ElementStore:
    """In-memory collection of OSM elements keyed by id."""

    nodes: dict[int, OsmNode] = field(default_factory=dict)
    ways: dict[int, OsmWay] = field(default_factory=dict)
    relations: dict[int, OsmRelation] = field(default_factory=dict)

    def merge(self, other: ElementStore) -> None:
        """Merges another store into this one."""
        self.nodes.update(other.nodes)
        self.ways.update(other.ways)
        self.relations.update(other.relations)


@dataclass(slots=True)
class Ring:
    """A closed ring of coordinates (first point equals last)."""

    points: list[LatLon]

    def is_closed(self) -> bool:
        """Returns True when the ring has at least 4 points and is closed."""
        if len(self.points) < 4:
            return False
        first = self.points[0]
        last = self.points[-1]
        return first.lat == last.lat and first.lon == last.lon


@dataclass(slots=True)
class Polygon:
    """A polygon with one outer ring and zero or more inner rings."""

    outer: Ring
    inners: list[Ring] = field(default_factory=list)


@dataclass(slots=True)
class MultiPolygon:
    """A collection of polygons representing relation geometry."""

    polygons: list[Polygon] = field(default_factory=list)
    relation_id: int | None = None
    name: str | None = None

    def is_empty(self) -> bool:
        """Returns True when there are no polygons."""
        return not self.polygons

    def merge(self, other: MultiPolygon) -> MultiPolygon:
        """Returns a new multipolygon combining both geometries."""
        return MultiPolygon(
            polygons=[*self.polygons, *other.polygons],
            relation_id=self.relation_id,
            name=self.name or other.name,
        )

    def bbox(self) -> tuple[float, float, float, float] | None:
        """Returns (min_lon, min_lat, max_lon, max_lat) or None if empty."""
        lons: list[float] = []
        lats: list[float] = []
        for polygon in self.polygons:
            for ring in (polygon.outer, *polygon.inners):
                for point in ring.points:
                    lons.append(point.lon)
                    lats.append(point.lat)
        if not lons:
            return None
        return min(lons), min(lats), max(lons), max(lats)
