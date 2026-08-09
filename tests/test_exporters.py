"""Tests for geometry exporters."""

from __future__ import annotations

import json
import pathlib
import re
import tempfile
import unittest

from boundarykit import models
from boundarykit.exporters import geojson
from boundarykit.exporters import poly
from boundarykit.exporters import svg
from boundarykit.exporters import wkt


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
        self.assertEqual(payload["properties"]["name"], "Sample")
        self.assertEqual(payload["geometry"]["type"], "MultiPolygon")

    def test_geojson_feature_name_with_quotes_and_newlines(self) -> None:
        geom = _sample_geometry()
        geom.name = 'Line "One"\nLine Two'
        payload = json.loads(
            geojson.GeoJsonExporter(as_feature=True).dumps(geom)
        )
        self.assertEqual(payload["properties"]["name"], 'Line "One"\nLine Two')

    def test_geojson_enforces_rfc7946_winding(self) -> None:
        # Clockwise outer (lon/lat) and counterclockwise inner in source.
        outer = models.Ring(
            points=[
                models.LatLon(0, 0),
                models.LatLon(2, 0),
                models.LatLon(2, 2),
                models.LatLon(0, 2),
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
        geom = models.MultiPolygon(
            polygons=[models.Polygon(outer=outer, inners=[inner])]
        )
        payload = json.loads(geojson.GeoJsonExporter().dumps(geom))
        outer_coords = payload["coordinates"][0][0]
        inner_coords = payload["coordinates"][0][1]
        self.assertGreater(_coords_signed_area(outer_coords), 0.0)
        self.assertLess(_coords_signed_area(inner_coords), 0.0)

    def test_poly_flattens_multiline_name(self) -> None:
        geom = _sample_geometry()
        geom.name = "Line One\nLine Two"
        text = poly.PolyExporter().dumps(geom)
        self.assertEqual(text.splitlines()[0], "Line One Line Two")

    def test_poly_end_name_falls_back_to_relation_id(self) -> None:
        geom = _sample_geometry()
        geom.name = "END"
        text = poly.PolyExporter().dumps(geom)
        self.assertEqual(text.splitlines()[0], "relation_42")

    def test_poly_name_with_quotes(self) -> None:
        geom = _sample_geometry()
        geom.name = 'Area "Quoted"'
        text = poly.PolyExporter().dumps(geom)
        self.assertEqual(text.splitlines()[0], 'Area "Quoted"')

    def test_poly_multiple_polygons_inner_markers(self) -> None:
        geom = models.MultiPolygon(
            polygons=[
                models.Polygon(
                    outer=_square_ring(0.0, 0.0, 2.0),
                    inners=[_square_ring(0.5, 0.5, 0.5)],
                ),
                models.Polygon(
                    outer=_square_ring(10.0, 10.0, 2.0),
                    inners=[_square_ring(10.5, 10.5, 0.5)],
                ),
            ],
            name="Multi",
        )
        text = poly.PolyExporter().dumps(geom)
        self.assertIn("\n1\n", text)
        self.assertIn("\n!2\n", text)
        self.assertIn("\n3\n", text)
        self.assertIn("\n!4\n", text)

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

    def test_svg_preserves_aspect_ratio(self) -> None:
        # Wide rectangle: lon span 4, lat span 1 — must not stretch to canvas.
        outer = models.Ring(
            points=[
                models.LatLon(0, 0),
                models.LatLon(0, 4),
                models.LatLon(1, 4),
                models.LatLon(1, 0),
                models.LatLon(0, 0),
            ]
        )
        geom = models.MultiPolygon(
            polygons=[models.Polygon(outer=outer)],
            name="Wide",
        )
        exporter = svg.SvgExporter(width=800, height=600, padding=0.0)
        text = exporter.dumps(geom)
        match = re.search(
            r"M([0-9.]+),([0-9.]+) L([0-9.]+),([0-9.]+) "
            r"L([0-9.]+),([0-9.]+)",
            text,
        )
        self.assertIsNotNone(match)
        assert match is not None
        x0 = float(match.group(1))
        x1 = float(match.group(3))
        y1 = float(match.group(4))
        y2 = float(match.group(6))
        pixel_width = abs(x1 - x0)
        pixel_height = abs(y2 - y1)
        # Geographic aspect lon/lat = 4/1; pixel aspect should match.
        self.assertAlmostEqual(pixel_width / pixel_height, 4.0, places=2)
        self.assertLessEqual(pixel_width, 800.0)
        self.assertLess(pixel_height, 600.0)

    def test_export_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "out.wkt"
            wkt.WktExporter().export(_sample_geometry(), path)
            self.assertTrue(path.is_file())
            self.assertIn("MULTIPOLYGON", path.read_text(encoding="utf-8"))

    def test_svg_empty_geometry(self) -> None:
        geom = models.MultiPolygon(polygons=[], name="Empty")
        text = svg.SvgExporter().dumps(geom)
        self.assertIn("<svg", text)
        self.assertIn("(empty)", text)
        self.assertIn("Empty", text)
        self.assertNotIn("<path", text)


def _square_ring(lat0: float, lon0: float, size: float) -> models.Ring:
    return models.Ring(
        points=[
            models.LatLon(lat0, lon0),
            models.LatLon(lat0, lon0 + size),
            models.LatLon(lat0 + size, lon0 + size),
            models.LatLon(lat0 + size, lon0),
            models.LatLon(lat0, lon0),
        ]
    )


def _coords_signed_area(coords: list[list[float]]) -> float:
    """Shoelace signed area for [lon, lat] rings; positive is CCW."""
    total = 0.0
    for index in range(len(coords) - 1):
        x1, y1 = coords[index]
        x2, y2 = coords[index + 1]
        total += x1 * y2 - x2 * y1
    return total / 2.0


if __name__ == "__main__":
    unittest.main()
