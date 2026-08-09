"""Tests for geometry exporters."""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from osm_geometry import models
from osm_geometry.exporters import geojson
from osm_geometry.exporters import poly
from osm_geometry.exporters import svg
from osm_geometry.exporters import wkt


def _sample_geometry() -> models.MultiPolygon:
    outer = models.Ring(
        points=[
            models.LatLon(0, 0),
            models.LatLon(0, 2),
            models.LatLon(2, 2),
            models.LatLon(2, 0),
            models.LatLon(0, 0),
        ]
    )
    inner = models.Ring(
        points=[
            models.LatLon(0.5, 0.5),
            models.LatLon(0.5, 1.5),
            models.LatLon(1.5, 1.5),
            models.LatLon(1.5, 0.5),
            models.LatLon(0.5, 0.5),
        ]
    )
    return models.MultiPolygon(
        polygons=[models.Polygon(outer=outer, inners=[inner])],
        relation_id=42,
        name="Sample",
    )


class ExportersTest(unittest.TestCase):
    """Tests poly/geojson/wkt/svg exporters."""

    def test_poly_contains_outer_and_inner_markers(self) -> None:
        text = poly.PolyExporter().dumps(_sample_geometry())
        self.assertIn("Sample", text)
        self.assertIn("\n1\n", text)
        self.assertIn("\n!2\n", text)
        self.assertTrue(text.strip().endswith("END"))

    def test_geojson_geometry_default(self) -> None:
        payload = json.loads(
            geojson.GeoJsonExporter().dumps(_sample_geometry())
        )
        self.assertEqual(payload["type"], "MultiPolygon")
        self.assertEqual(len(payload["coordinates"]), 1)
        self.assertEqual(len(payload["coordinates"][0]), 2)

    def test_geojson_feature(self) -> None:
        payload = json.loads(
            geojson.GeoJsonExporter(as_feature=True).dumps(_sample_geometry())
        )
        self.assertEqual(payload["type"], "Feature")
        self.assertEqual(payload["properties"]["osm_relation_id"], 42)
        self.assertEqual(payload["geometry"]["type"], "MultiPolygon")

    def test_wkt_and_ewkt(self) -> None:
        wkt_text = wkt.WktExporter().dumps(_sample_geometry())
        self.assertTrue(wkt_text.startswith("MULTIPOLYGON"))
        ewkt_text = wkt.WktExporter(ewkt=True).dumps(_sample_geometry())
        self.assertTrue(ewkt_text.startswith("SRID=4326;MULTIPOLYGON"))

    def test_svg_contains_path(self) -> None:
        svg_text = svg.SvgExporter().dumps(_sample_geometry())
        self.assertIn("<svg", svg_text)
        self.assertIn("<path", svg_text)
        self.assertIn("Sample", svg_text)

    def test_export_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "out.wkt"
            wkt.WktExporter().export(_sample_geometry(), path)
            self.assertTrue(path.is_file())
            self.assertIn("MULTIPOLYGON", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
