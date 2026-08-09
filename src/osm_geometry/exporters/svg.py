"""SVG preview exporter."""

from __future__ import annotations

import pathlib
import xml.sax.saxutils as saxutils

from osm_geometry import models


class SvgExporter:
    """Exports a simple SVG preview of the multipolygon."""

    format_id = "svg"
    file_extension = ".svg"

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        padding: float = 0.05,
    ) -> None:
        self._width = width
        self._height = height
        self._padding = padding

    def export(self, geometry: models.MultiPolygon, path: pathlib.Path) -> None:
        """Writes SVG to path.

        Args:
            geometry: Geometry to export.
            path: Destination file path.
        """
        path.write_text(self.dumps(geometry), encoding="utf-8")

    def dumps(self, geometry: models.MultiPolygon) -> str:
        """Returns SVG markup for geometry."""
        bbox = geometry.bbox()
        title = geometry.name or (
            f"relation {geometry.relation_id}"
            if geometry.relation_id is not None
            else "polygon"
        )
        if bbox is None:
            return (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{self._width}" height="{self._height}">'
                f'<text x="10" y="20">{saxutils.escape(title)} (empty)</text>'
                "</svg>\n"
            )

        min_lon, min_lat, max_lon, max_lat = bbox
        lon_span = max(max_lon - min_lon, 1e-12)
        lat_span = max(max_lat - min_lat, 1e-12)
        pad_lon = lon_span * self._padding
        pad_lat = lat_span * self._padding
        min_lon -= pad_lon
        max_lon += pad_lon
        min_lat -= pad_lat
        max_lat += pad_lat
        lon_span = max_lon - min_lon
        lat_span = max_lat - min_lat

        scale = min(self._width / lon_span, self._height / lat_span)
        used_width = lon_span * scale
        used_height = lat_span * scale
        offset_x = (self._width - used_width) / 2.0
        offset_y = (self._height - used_height) / 2.0
        projection = _SvgProjection(
            min_lon=min_lon,
            max_lat=max_lat,
            lon_span=lon_span,
            lat_span=lat_span,
            used_width=used_width,
            used_height=used_height,
            offset_x=offset_x,
            offset_y=offset_y,
        )

        paths: list[str] = []
        for polygon in geometry.polygons:
            d_parts = [_ring_path(polygon.outer, projection)]
            for inner in polygon.inners:
                d_parts.append(_ring_path(inner, projection))
            d_attr = " ".join(d_parts)
            paths.append(
                f'<path d="{d_attr}" fill="#4a90d9" fill-opacity="0.35" '
                f'stroke="#1f4e79" stroke-width="1.5" fill-rule="evenodd"/>'
            )

        body = "\n  ".join(paths)
        view_box = f"0 0 {self._width} {self._height}"
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self._width}" height="{self._height}" '
            f'viewBox="{view_box}">\n'
            f"  <title>{saxutils.escape(title)}</title>\n"
            f'  <rect width="100%" height="100%" fill="#f7f7f7"/>\n'
            f"  {body}\n"
            f"</svg>\n"
        )


class _SvgProjection:
    """Uniform-scale lon/lat to SVG pixel mapping."""

    __slots__ = (
        "min_lon",
        "max_lat",
        "lon_span",
        "lat_span",
        "used_width",
        "used_height",
        "offset_x",
        "offset_y",
    )

    def __init__(
        self,
        *,
        min_lon: float,
        max_lat: float,
        lon_span: float,
        lat_span: float,
        used_width: float,
        used_height: float,
        offset_x: float,
        offset_y: float,
    ) -> None:
        self.min_lon = min_lon
        self.max_lat = max_lat
        self.lon_span = lon_span
        self.lat_span = lat_span
        self.used_width = used_width
        self.used_height = used_height
        self.offset_x = offset_x
        self.offset_y = offset_y

    def project(self, point: models.LatLon) -> tuple[float, float]:
        x = (
            self.offset_x
            + (point.lon - self.min_lon) / self.lon_span * self.used_width
        )
        y = (
            self.offset_y
            + (self.max_lat - point.lat) / self.lat_span * self.used_height
        )
        return x, y


def _ring_path(ring: models.Ring, projection: _SvgProjection) -> str:
    commands: list[str] = []
    for index, point in enumerate(ring.points):
        x, y = projection.project(point)
        prefix = "M" if index == 0 else "L"
        commands.append(f"{prefix}{x:.2f},{y:.2f}")
    commands.append("Z")
    return " ".join(commands)
