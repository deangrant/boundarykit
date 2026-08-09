"""Tests for relation geometry assembly."""

from __future__ import annotations

import pathlib
import unittest

from boundarykit import assembler
from boundarykit import client
from boundarykit import models

_FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _node(osm_id: int, lat: float, lon: float) -> models.OsmNode:
    return models.OsmNode(osm_id=osm_id, coordinate=models.LatLon(lat, lon))


def _way(osm_id: int, node_ids: list[int]) -> models.OsmWay:
    return models.OsmWay(osm_id=osm_id, node_ids=node_ids)


def _member(
    member_type: str,
    ref: int,
    role: str = "outer",
) -> models.OsmMember:
    return models.OsmMember(member_type=member_type, ref=ref, role=role)


def _closed_square_nodes(
    start_id: int,
    origin: tuple[float, float],
    size: float = 1.0,
) -> list[models.OsmNode]:
    lat0, lon0 = origin
    return [
        _node(start_id, lat0, lon0),
        _node(start_id + 1, lat0, lon0 + size),
        _node(start_id + 2, lat0 + size, lon0 + size),
        _node(start_id + 3, lat0 + size, lon0),
    ]


class RelationAssemblerTest(unittest.TestCase):
    """Tests RelationAssembler."""

    def test_outer_and_inner(self) -> None:
        store = client.parse_osm_xml(
            (_FIXTURES / "simple_relation.xml").read_bytes()
        )
        geom = assembler.RelationAssembler().assemble(store, 100)
        self.assertEqual(len(geom.polygons), 1)
        self.assertEqual(len(geom.polygons[0].inners), 1)
        self.assertEqual(geom.name, "Test Area")
        self.assertTrue(geom.polygons[0].outer.is_closed())

    def test_chains_open_ways(self) -> None:
        store = client.parse_osm_xml(
            (_FIXTURES / "open_ways_relation.xml").read_bytes()
        )
        geom = assembler.RelationAssembler().assemble(store, 100)
        self.assertEqual(len(geom.polygons), 1)
        self.assertTrue(geom.polygons[0].outer.is_closed())
        self.assertGreaterEqual(len(geom.polygons[0].outer.points), 4)

    def test_nested_relation_merge(self) -> None:
        store = client.parse_osm_xml(
            (_FIXTURES / "nested_relation.xml").read_bytes()
        )
        geom = assembler.RelationAssembler().assemble(store, 100)
        self.assertEqual(len(geom.polygons), 2)
        self.assertEqual(geom.name, "Parent")

    def test_missing_way_raises(self) -> None:
        store = models.ElementStore(
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[_member("way", 99, "outer")],
                )
            }
        )
        with self.assertRaises(assembler.AssemblyError):
            assembler.RelationAssembler().assemble(store, 1)

    def test_missing_node_raises(self) -> None:
        store = models.ElementStore(
            nodes={1: _node(1, 0.0, 0.0), 2: _node(2, 0.0, 1.0)},
            ways={10: _way(10, [1, 2, 3, 1])},
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[_member("way", 10, "outer")],
                )
            },
        )
        with self.assertRaises(assembler.AssemblyError):
            assembler.RelationAssembler().assemble(store, 1)

    def test_ambiguous_junction_raises(self) -> None:
        # Three open ways meet at (0, 0); extending is ambiguous.
        store = models.ElementStore(
            nodes={
                1: _node(1, 0.0, 0.0),
                2: _node(2, 0.0, 1.0),
                3: _node(3, 1.0, 0.0),
                4: _node(4, -1.0, 0.0),
            },
            ways={
                10: _way(10, [2, 1]),
                11: _way(11, [1, 3]),
                12: _way(12, [1, 4]),
            },
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[
                        _member("way", 10, "outer"),
                        _member("way", 11, "outer"),
                        _member("way", 12, "outer"),
                    ],
                )
            },
        )
        with self.assertRaises(assembler.AssemblyError):
            assembler.RelationAssembler().assemble(store, 1)

    def test_unclosed_ring_raises(self) -> None:
        store = models.ElementStore(
            nodes={
                1: _node(1, 0.0, 0.0),
                2: _node(2, 0.0, 1.0),
                3: _node(3, 1.0, 1.0),
            },
            ways={10: _way(10, [1, 2, 3])},
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[_member("way", 10, "outer")],
                )
            },
        )
        with self.assertRaises(assembler.AssemblyError):
            assembler.RelationAssembler().assemble(store, 1)

    def test_inner_outside_outer_raises(self) -> None:
        outer_nodes = _closed_square_nodes(1, (0.0, 0.0), 1.0)
        inner_nodes = _closed_square_nodes(10, (5.0, 5.0), 1.0)
        store = models.ElementStore(
            nodes={n.osm_id: n for n in (*outer_nodes, *inner_nodes)},
            ways={
                100: _way(100, [1, 2, 3, 4, 1]),
                101: _way(101, [10, 11, 12, 13, 10]),
            },
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[
                        _member("way", 100, "outer"),
                        _member("way", 101, "inner"),
                    ],
                )
            },
        )
        with self.assertRaises(assembler.AssemblyError):
            assembler.RelationAssembler().assemble(store, 1)

    def test_inner_in_two_outers_raises(self) -> None:
        # Overlapping outers both contain the inner probe point.
        outer_a = _closed_square_nodes(1, (0.0, 0.0), 3.0)
        outer_b = _closed_square_nodes(10, (0.5, 0.5), 3.0)
        inner = _closed_square_nodes(20, (1.0, 1.0), 0.5)
        store = models.ElementStore(
            nodes={n.osm_id: n for n in (*outer_a, *outer_b, *inner)},
            ways={
                100: _way(100, [1, 2, 3, 4, 1]),
                101: _way(101, [10, 11, 12, 13, 10]),
                102: _way(102, [20, 21, 22, 23, 20]),
            },
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[
                        _member("way", 100, "outer"),
                        _member("way", 101, "outer"),
                        _member("way", 102, "inner"),
                    ],
                )
            },
        )
        with self.assertRaises(assembler.AssemblyError):
            assembler.RelationAssembler().assemble(store, 1)

    def test_label_role_skipped(self) -> None:
        outer_nodes = _closed_square_nodes(1, (0.0, 0.0), 1.0)
        store = models.ElementStore(
            nodes={
                **{n.osm_id: n for n in outer_nodes},
                50: _node(50, 0.5, 0.5),
            },
            ways={
                100: _way(100, [1, 2, 3, 4, 1]),
                101: _way(101, [50, 1]),
            },
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[
                        _member("way", 100, "outer"),
                        _member("way", 101, "label"),
                    ],
                )
            },
        )
        geom = assembler.RelationAssembler().assemble(store, 1)
        self.assertEqual(len(geom.polygons), 1)
        self.assertEqual(len(geom.polygons[0].inners), 0)

    def test_unknown_way_role_raises(self) -> None:
        outer_nodes = _closed_square_nodes(1, (0.0, 0.0), 1.0)
        store = models.ElementStore(
            nodes={n.osm_id: n for n in outer_nodes},
            ways={100: _way(100, [1, 2, 3, 4, 1])},
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[_member("way", 100, "weird")],
                )
            },
        )
        with self.assertRaises(assembler.AssemblyError):
            assembler.RelationAssembler().assemble(store, 1)

    def test_nested_relation_inner_role_raises(self) -> None:
        child_nodes = _closed_square_nodes(1, (0.0, 0.0), 1.0)
        parent_nodes = _closed_square_nodes(10, (10.0, 10.0), 1.0)
        store = models.ElementStore(
            nodes={n.osm_id: n for n in (*child_nodes, *parent_nodes)},
            ways={
                100: _way(100, [1, 2, 3, 4, 1]),
                101: _way(101, [10, 11, 12, 13, 10]),
            },
            relations={
                200: models.OsmRelation(
                    osm_id=200,
                    members=[_member("way", 100, "outer")],
                    tags={"type": "multipolygon"},
                ),
                100: models.OsmRelation(
                    osm_id=100,
                    members=[
                        _member("way", 101, "outer"),
                        _member("relation", 200, "inner"),
                    ],
                    tags={"type": "multipolygon"},
                ),
            },
        )
        with self.assertRaises(assembler.AssemblyError):
            assembler.RelationAssembler().assemble(store, 100)

    def test_shared_nested_relation_is_not_cyclic(self) -> None:
        # Parent references the same child twice (shared nested ref / diamond).
        child_nodes = _closed_square_nodes(1, (0.0, 0.0), 1.0)
        store = models.ElementStore(
            nodes={n.osm_id: n for n in child_nodes},
            ways={10: _way(10, [1, 2, 3, 4, 1])},
            relations={
                200: models.OsmRelation(
                    osm_id=200,
                    members=[_member("way", 10, "outer")],
                    tags={"type": "multipolygon"},
                ),
                100: models.OsmRelation(
                    osm_id=100,
                    members=[
                        _member("relation", 200, "subarea"),
                        _member("relation", 200, "subarea"),
                    ],
                    tags={"type": "boundary", "name": "Parent"},
                ),
            },
        )
        geom = assembler.RelationAssembler().assemble(store, 100)
        self.assertEqual(len(geom.polygons), 2)
        self.assertEqual(geom.name, "Parent")

    def test_true_relation_cycle_raises(self) -> None:
        nodes_a = _closed_square_nodes(1, (0.0, 0.0), 1.0)
        nodes_b = _closed_square_nodes(10, (5.0, 5.0), 1.0)
        store = models.ElementStore(
            nodes={n.osm_id: n for n in (*nodes_a, *nodes_b)},
            ways={
                10: _way(10, [1, 2, 3, 4, 1]),
                20: _way(20, [10, 11, 12, 13, 10]),
            },
            relations={
                100: models.OsmRelation(
                    osm_id=100,
                    members=[
                        _member("way", 10, "outer"),
                        _member("relation", 200, "subarea"),
                    ],
                ),
                200: models.OsmRelation(
                    osm_id=200,
                    members=[
                        _member("way", 20, "outer"),
                        _member("relation", 100, "subarea"),
                    ],
                ),
            },
        )
        with self.assertRaises(assembler.AssemblyError) as ctx:
            assembler.RelationAssembler().assemble(store, 100)
        self.assertIn("Cyclic", str(ctx.exception))

    def test_multi_outer_two_inners_ownership(self) -> None:
        outer_a = _closed_square_nodes(1, (0.0, 0.0), 2.0)
        outer_b = _closed_square_nodes(10, (10.0, 10.0), 2.0)
        inner_a = _closed_square_nodes(20, (0.5, 0.5), 0.5)
        inner_b = _closed_square_nodes(30, (10.5, 10.5), 0.5)
        store = models.ElementStore(
            nodes={
                n.osm_id: n for n in (*outer_a, *outer_b, *inner_a, *inner_b)
            },
            ways={
                100: _way(100, [1, 2, 3, 4, 1]),
                101: _way(101, [10, 11, 12, 13, 10]),
                102: _way(102, [20, 21, 22, 23, 20]),
                103: _way(103, [30, 31, 32, 33, 30]),
            },
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[
                        _member("way", 100, "outer"),
                        _member("way", 101, "outer"),
                        _member("way", 102, "inner"),
                        _member("way", 103, "inner"),
                    ],
                )
            },
        )
        geom = assembler.RelationAssembler().assemble(store, 1)
        self.assertEqual(len(geom.polygons), 2)
        ownership = {
            polygon.outer.points[0]: len(polygon.inners)
            for polygon in geom.polygons
        }
        self.assertEqual(ownership[models.LatLon(0.0, 0.0)], 1)
        self.assertEqual(ownership[models.LatLon(10.0, 10.0)], 1)
        for polygon in geom.polygons:
            self.assertEqual(len(polygon.inners), 1)
            probe = polygon.inners[0].points[0]
            # pylint: disable-next=protected-access
            self.assertTrue(assembler._point_in_ring(probe, polygon.outer))

    def test_inner_role_casing(self) -> None:
        outer_nodes = _closed_square_nodes(1, (0.0, 0.0), 2.0)
        inner_nodes = _closed_square_nodes(10, (0.5, 0.5), 0.5)
        store = models.ElementStore(
            nodes={n.osm_id: n for n in (*outer_nodes, *inner_nodes)},
            ways={
                100: _way(100, [1, 2, 3, 4, 1]),
                101: _way(101, [10, 11, 12, 13, 10]),
            },
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[
                        _member("way", 100, "OUTER"),
                        _member("way", 101, "INNER"),
                    ],
                )
            },
        )
        geom = assembler.RelationAssembler().assemble(store, 1)
        self.assertEqual(len(geom.polygons), 1)
        self.assertEqual(len(geom.polygons[0].inners), 1)

    def test_fetch_missing_root_invoked_and_merged(self) -> None:
        nodes = _closed_square_nodes(1, (0.0, 0.0), 1.0)
        fetched = models.ElementStore(
            nodes={n.osm_id: n for n in nodes},
            ways={10: _way(10, [1, 2, 3, 4, 1])},
            relations={
                100: models.OsmRelation(
                    osm_id=100,
                    members=[_member("way", 10, "outer")],
                    tags={"name": "Fetched"},
                )
            },
        )
        calls: list[int] = []

        def fetch_missing(relation_id: int) -> models.ElementStore:
            calls.append(relation_id)
            return fetched

        store = models.ElementStore()
        geom = assembler.RelationAssembler(
            fetch_missing=fetch_missing
        ).assemble(store, 100)
        self.assertEqual(calls, [100])
        self.assertEqual(len(geom.polygons), 1)
        self.assertEqual(geom.name, "Fetched")
        self.assertIn(100, store.relations)

    def test_fetch_missing_nested_child_invoked_and_merged(self) -> None:
        parent_nodes = _closed_square_nodes(1, (0.0, 0.0), 1.0)
        child_nodes = _closed_square_nodes(10, (5.0, 5.0), 1.0)
        child_store = models.ElementStore(
            nodes={n.osm_id: n for n in child_nodes},
            ways={20: _way(20, [10, 11, 12, 13, 10])},
            relations={
                200: models.OsmRelation(
                    osm_id=200,
                    members=[_member("way", 20, "outer")],
                    tags={"type": "multipolygon"},
                )
            },
        )
        store = models.ElementStore(
            nodes={n.osm_id: n for n in parent_nodes},
            ways={10: _way(10, [1, 2, 3, 4, 1])},
            relations={
                100: models.OsmRelation(
                    osm_id=100,
                    members=[
                        _member("way", 10, "outer"),
                        _member("relation", 200, "subarea"),
                    ],
                    tags={"type": "boundary", "name": "Parent"},
                )
            },
        )
        calls: list[int] = []

        def fetch_missing(relation_id: int) -> models.ElementStore:
            calls.append(relation_id)
            return child_store

        geom = assembler.RelationAssembler(
            fetch_missing=fetch_missing
        ).assemble(store, 100)
        self.assertEqual(calls, [200])
        self.assertEqual(len(geom.polygons), 2)
        self.assertIn(200, store.relations)

    def test_missing_relation_without_fetch_missing_raises(self) -> None:
        store = models.ElementStore()
        with self.assertRaises(assembler.AssemblyError) as ctx:
            assembler.RelationAssembler().assemble(store, 100)
        self.assertIn("not found", str(ctx.exception))

    def test_messy_multipolygon_fixture(self) -> None:
        store = client.parse_osm_xml(
            (_FIXTURES / "messy_multipolygon.xml").read_bytes()
        )
        geom = assembler.RelationAssembler().assemble(store, 100)
        self.assertEqual(len(geom.polygons), 2)
        self.assertEqual(geom.name, "Messy Parent")
        parent_polys = [
            polygon
            for polygon in geom.polygons
            if polygon.outer.points[0] == models.LatLon(0.0, 0.0)
        ]
        self.assertEqual(len(parent_polys), 1)
        self.assertEqual(len(parent_polys[0].inners), 1)


if __name__ == "__main__":
    unittest.main()
