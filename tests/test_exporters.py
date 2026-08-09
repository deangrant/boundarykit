"""Tests for geometry exporters."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from osm_geometry.exporters.geojson import GeoJsonExporter
from osm_geometry.exporters.poly import PolyExporter
from osm_geometry.exporters.svg import SvgExporter
from osm_geometry.exporters.wkt import WktExporter
from osm_geometry.models import LatLon
from osm_geometry.models import MultiPolygon
from osm_geometry.models import Polygon
from osm_geometry.models import Ring


def _sample_geometry() -> MultiPolygon:
    outer = Ring(
        points=[
            LatLon(0, 0),
            LatLon(0, 2),
            LatLon(2, 2),
            LatLon(2, 0),
            LatLon(0, 0),
        ]
    )
    inner = Ring(
        points=[
            LatLon(0.5, 0.5),
            LatLon(0.5, 1.5),
            LatLon(1.5, 1.5),
            LatLon(1.5, 0.5),
            LatLon(0.5, 0.5),
        ]
    )
    return MultiPolygon(
        polygons=[Polygon(outer=outer, inners=[inner])],
        relation_id=42,
        name="Sample",
    )


class ExportersTest(unittest.TestCase):
    """Tests poly/geojson/wkt/svg exporters."""

    def test_poly_contains_outer_and_inner_markers(self) -> None:
        text = PolyExporter().dumps(_sample_geometry())
        self.assertIn("Sample", text)
        self.assertIn("\n1\n", text)
        self.assertIn("\n!2\n", text)
        self.assertTrue(text.strip().endswith("END"))

    def test_geojson_geometry_default(self) -> None:
        payload = json.loads(GeoJsonExporter().dumps(_sample_geometry()))
        self.assertEqual(payload["type"], "MultiPolygon")
        self.assertEqual(len(payload["coordinates"]), 1)
        self.assertEqual(len(payload["coordinates"][0]), 2)

    def test_geojson_feature(self) -> None:
        payload = json.loads(
            GeoJsonExporter(as_feature=True).dumps(_sample_geometry())
        )
        self.assertEqual(payload["type"], "Feature")
        self.assertEqual(payload["properties"]["osm_relation_id"], 42)
        self.assertEqual(payload["geometry"]["type"], "MultiPolygon")

    def test_wkt_and_ewkt(self) -> None:
        wkt = WktExporter().dumps(_sample_geometry())
        self.assertTrue(wkt.startswith("MULTIPOLYGON"))
        ewkt = WktExporter(ewkt=True).dumps(_sample_geometry())
        self.assertTrue(ewkt.startswith("SRID=4326;MULTIPOLYGON"))

    def test_svg_contains_path(self) -> None:
        svg = SvgExporter().dumps(_sample_geometry())
        self.assertIn("<svg", svg)
        self.assertIn("<path", svg)
        self.assertIn("Sample", svg)

    def test_export_writes_file(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.wkt"
            WktExporter().export(_sample_geometry(), path)
            self.assertTrue(path.is_file())
            self.assertIn("MULTIPOLYGON", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
