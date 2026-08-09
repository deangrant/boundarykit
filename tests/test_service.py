"""Tests for RelationGeometryService wiring."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from osm_geometry import assembler
from osm_geometry import client
from osm_geometry import models
from osm_geometry import service
from osm_geometry import simplify
from osm_geometry.exporters import geojson
from osm_geometry.exporters import wkt

_FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class _FakeClient:
    """In-memory client returning a fixture store."""

    def __init__(self, store: models.ElementStore) -> None:
        self._store = store

    def fetch_relation_full(self, relation_id: int) -> models.ElementStore:
        del relation_id  # Unused.
        return self._store


class RelationGeometryServiceTest(unittest.TestCase):
    """Tests service build/export."""

    def test_run_writes_outputs(self) -> None:
        store = client.parse_osm_xml(
            (_FIXTURES / "simple_relation.xml").read_bytes()
        )
        geojson_exporter = geojson.GeoJsonExporter()
        wkt_exporter = wkt.WktExporter(ewkt=True)
        geometry_service = service.RelationGeometryService(
            osm_client=_FakeClient(store),
            relation_assembler=assembler.RelationAssembler(),
            geometry_simplifier=simplify.GeometrySimplifier(),
            exporters={
                geojson_exporter.format_id: geojson_exporter,
                wkt_exporter.format_id: wkt_exporter,
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = geometry_service.run(
                100,
                ["geojson", "wkt"],
                output_dir=pathlib.Path(tmp),
            )
            self.assertEqual(len(paths), 2)
            for path in paths:
                self.assertTrue(path.is_file())

    def test_export_dedupes_formats(self) -> None:
        store = client.parse_osm_xml(
            (_FIXTURES / "simple_relation.xml").read_bytes()
        )
        geojson_exporter = geojson.GeoJsonExporter()
        wkt_exporter = wkt.WktExporter()
        geometry_service = service.RelationGeometryService(
            osm_client=_FakeClient(store),
            relation_assembler=assembler.RelationAssembler(),
            geometry_simplifier=simplify.GeometrySimplifier(),
            exporters={
                geojson_exporter.format_id: geojson_exporter,
                wkt_exporter.format_id: wkt_exporter,
            },
        )
        geometry = geometry_service.build_geometry(100)
        with tempfile.TemporaryDirectory() as tmp:
            paths = geometry_service.export(
                geometry,
                ["geojson", "geojson", "wkt"],
                output_dir=pathlib.Path(tmp),
            )
            self.assertEqual(len(paths), 2)
            self.assertEqual(
                [path.suffix for path in paths], [".geojson", ".wkt"]
            )


if __name__ == "__main__":
    unittest.main()
