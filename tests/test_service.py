"""Tests for RelationGeometryService wiring."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from osm_geometry.assembler import RelationAssembler
from osm_geometry.client import parse_osm_xml
from osm_geometry.exporters.geojson import GeoJsonExporter
from osm_geometry.exporters.wkt import WktExporter
from osm_geometry.models import ElementStore
from osm_geometry.service import RelationGeometryService
from osm_geometry.simplify import GeometrySimplifier

_FIXTURES = Path(__file__).parent / "fixtures"


class _FakeClient:
    """In-memory client returning a fixture store."""

    def __init__(self, store: ElementStore) -> None:
        self._store = store

    def fetch_relation_full(self, relation_id: int) -> ElementStore:
        del relation_id
        return self._store


class RelationGeometryServiceTest(unittest.TestCase):
    """Tests service build/export."""

    def test_run_writes_outputs(self) -> None:
        store = parse_osm_xml((_FIXTURES / "simple_relation.xml").read_bytes())
        service = RelationGeometryService(
            client=_FakeClient(store),
            assembler=RelationAssembler(),
            simplifier=GeometrySimplifier(),
            exporters={
                "geojson": GeoJsonExporter(),
                "wkt": WktExporter(ewkt=True),
            },
        )
        with TemporaryDirectory() as tmp:
            paths = service.run(
                100,
                ["geojson", "wkt"],
                output_dir=Path(tmp),
            )
            self.assertEqual(len(paths), 2)
            for path in paths:
                self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
