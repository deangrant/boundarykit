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

    def test_unknown_format_raises(self) -> None:
        geometry_service = _service_for_fixture("simple_relation.xml")
        geometry = geometry_service.build_geometry(100)
        with self.assertRaises(ValueError) as ctx:
            geometry_service.export(geometry, ["nope"])
        self.assertIn("Unknown export format", str(ctx.exception))

    def test_empty_formats_raises(self) -> None:
        geometry_service = _service_for_fixture("simple_relation.xml")
        geometry = geometry_service.build_geometry(100)
        with self.assertRaises(ValueError) as ctx:
            geometry_service.export(geometry, ["", "  "])
        self.assertIn("At least one export format", str(ctx.exception))

    def test_empty_geometry_raises_assembly_error(self) -> None:
        store = models.ElementStore(
            relations={
                1: models.OsmRelation(
                    osm_id=1,
                    members=[],
                    tags={"type": "multipolygon", "name": "Empty"},
                )
            }
        )
        geojson_exporter = geojson.GeoJsonExporter()
        geometry_service = service.RelationGeometryService(
            osm_client=_FakeClient(store),
            relation_assembler=assembler.RelationAssembler(),
            geometry_simplifier=simplify.GeometrySimplifier(),
            exporters={geojson_exporter.format_id: geojson_exporter},
        )
        with self.assertRaises(assembler.AssemblyError) as ctx:
            geometry_service.build_geometry(1)
        self.assertIn("no polygon geometry", str(ctx.exception))

    def test_export_sanitizes_unsafe_osm_name(self) -> None:
        store = client.parse_osm_xml(
            (_FIXTURES / "simple_relation.xml").read_bytes()
        )
        store.relations[100].tags["name"] = "../bad name/with spaces"
        geometry_service = service.RelationGeometryService(
            osm_client=_FakeClient(store),
            relation_assembler=assembler.RelationAssembler(),
            geometry_simplifier=simplify.GeometrySimplifier(),
            exporters={
                geojson.GeoJsonExporter().format_id: geojson.GeoJsonExporter()
            },
        )
        geometry = geometry_service.build_geometry(100)
        with tempfile.TemporaryDirectory() as tmp:
            paths = geometry_service.export(
                geometry,
                ["geojson"],
                output_dir=pathlib.Path(tmp),
            )
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].name, "bad_name_with_spaces.geojson")
            self.assertTrue(paths[0].is_file())


def _service_for_fixture(filename: str) -> service.RelationGeometryService:
    store = client.parse_osm_xml((_FIXTURES / filename).read_bytes())
    geojson_exporter = geojson.GeoJsonExporter()
    return service.RelationGeometryService(
        osm_client=_FakeClient(store),
        relation_assembler=assembler.RelationAssembler(),
        geometry_simplifier=simplify.GeometrySimplifier(),
        exporters={geojson_exporter.format_id: geojson_exporter},
    )


if __name__ == "__main__":
    unittest.main()
