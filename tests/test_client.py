"""Tests for OSM XML parsing."""

from __future__ import annotations

from pathlib import Path
import unittest

from osm_geometry.client import parse_osm_xml

_FIXTURES = Path(__file__).parent / "fixtures"


class ParseOsmXmlTest(unittest.TestCase):
    """Tests parse_osm_xml."""

    def test_parses_nodes_ways_relations(self) -> None:
        payload = (_FIXTURES / "simple_relation.xml").read_bytes()
        store = parse_osm_xml(payload)
        self.assertIn(1, store.nodes)
        self.assertEqual(store.nodes[1].coordinate.lat, 0.0)
        self.assertIn(10, store.ways)
        self.assertEqual(store.ways[10].node_ids[0], 1)
        self.assertIn(100, store.relations)
        self.assertEqual(store.relations[100].name, "Test Area")
        self.assertEqual(len(store.relations[100].members), 2)


if __name__ == "__main__":
    unittest.main()
