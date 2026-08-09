"""Tests for relation geometry assembly."""

from __future__ import annotations

from pathlib import Path
import unittest

from osm_geometry.assembler import RelationAssembler
from osm_geometry.client import parse_osm_xml

_FIXTURES = Path(__file__).parent / "fixtures"


class RelationAssemblerTest(unittest.TestCase):
    """Tests RelationAssembler."""

    def test_outer_and_inner(self) -> None:
        store = parse_osm_xml((_FIXTURES / "simple_relation.xml").read_bytes())
        geom = RelationAssembler().assemble(store, 100)
        self.assertEqual(len(geom.polygons), 1)
        self.assertEqual(len(geom.polygons[0].inners), 1)
        self.assertEqual(geom.name, "Test Area")
        self.assertTrue(geom.polygons[0].outer.is_closed())

    def test_chains_open_ways(self) -> None:
        store = parse_osm_xml(
            (_FIXTURES / "open_ways_relation.xml").read_bytes()
        )
        geom = RelationAssembler().assemble(store, 100)
        self.assertEqual(len(geom.polygons), 1)
        self.assertTrue(geom.polygons[0].outer.is_closed())
        self.assertGreaterEqual(len(geom.polygons[0].outer.points), 4)

    def test_nested_relation_merge(self) -> None:
        store = parse_osm_xml((_FIXTURES / "nested_relation.xml").read_bytes())
        geom = RelationAssembler().assemble(store, 100)
        self.assertEqual(len(geom.polygons), 2)
        self.assertEqual(geom.name, "Parent")


if __name__ == "__main__":
    unittest.main()
