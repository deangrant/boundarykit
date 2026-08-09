"""Tests for OSM XML parsing and API client limits."""

from __future__ import annotations

import io
import pathlib
import unittest
from urllib import error as urllib_error

from osm_geometry import client

_FIXTURES = pathlib.Path(__file__).parent / "fixtures"
_MINIMAL_OSM = b"""<?xml version="1.0"?>
<osm version="0.6">
  <relation id="1"/>
</osm>
"""


class ParseOsmXmlTest(unittest.TestCase):
    """Tests parse_osm_xml."""

    def test_parses_nodes_ways_relations(self) -> None:
        payload = (_FIXTURES / "simple_relation.xml").read_bytes()
        store = client.parse_osm_xml(payload)
        self.assertIn(1, store.nodes)
        self.assertEqual(store.nodes[1].coordinate.lat, 0.0)
        self.assertIn(10, store.ways)
        self.assertEqual(store.ways[10].node_ids[0], 1)
        self.assertIn(100, store.relations)
        self.assertEqual(store.relations[100].name, "Test Area")
        self.assertEqual(len(store.relations[100].members), 2)

    def test_node_missing_lat_raises_osm_client_error(self) -> None:
        payload = b"""<?xml version="1.0"?>
        <osm version="0.6">
          <node id="1" lon="0"/>
        </osm>
        """
        with self.assertRaises(client.OsmClientError) as ctx:
            client.parse_osm_xml(payload)
        self.assertIn("missing lat", str(ctx.exception))

    def test_way_nd_missing_ref_raises_osm_client_error(self) -> None:
        payload = b"""<?xml version="1.0"?>
        <osm version="0.6">
          <way id="10"><nd/></way>
        </osm>
        """
        with self.assertRaises(client.OsmClientError) as ctx:
            client.parse_osm_xml(payload)
        self.assertIn("missing ref", str(ctx.exception))

    def test_relation_member_missing_type_raises_osm_client_error(
        self,
    ) -> None:
        payload = b"""<?xml version="1.0"?>
        <osm version="0.6">
          <relation id="100">
            <member ref="10" role="outer"/>
          </relation>
        </osm>
        """
        with self.assertRaises(client.OsmClientError) as ctx:
            client.parse_osm_xml(payload)
        self.assertIn("missing type", str(ctx.exception))


class _FakeResponse:
    """Minimal urlopen response supporting chunked reads."""

    def __init__(
        self,
        body: bytes,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._buffer = io.BytesIO(body)
        self.headers = headers or {}

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        del args  # Unused.


class _FakeClock:
    """Deterministic monotonic clock and sleep recorder."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class OsmApiClientLimitsTest(unittest.TestCase):
    """Tests OsmApiClient size, budget, throttle, and retry behavior."""

    def test_oversized_body_raises(self) -> None:
        body = b"x" * 100

        def fake_urlopen(req: object, timeout: float = 0) -> _FakeResponse:
            del req, timeout  # Unused.
            return _FakeResponse(body)

        osm_client = client.OsmApiClient(
            urlopen=fake_urlopen,
            max_response_bytes=50,
            min_request_interval_seconds=0,
            max_relation_fetches=5,
        )
        with self.assertRaises(client.OsmClientError) as ctx:
            osm_client.fetch_relation_full(1)
        self.assertIn("exceeded limit", str(ctx.exception))

    def test_content_length_over_limit_raises(self) -> None:
        def fake_urlopen(req: object, timeout: float = 0) -> _FakeResponse:
            del req, timeout  # Unused.
            return _FakeResponse(
                _MINIMAL_OSM,
                headers={"Content-Length": "99999"},
            )

        osm_client = client.OsmApiClient(
            urlopen=fake_urlopen,
            max_response_bytes=100,
            min_request_interval_seconds=0,
            max_relation_fetches=5,
        )
        with self.assertRaises(client.OsmClientError) as ctx:
            osm_client.fetch_relation_full(1)
        self.assertIn("Content-Length", str(ctx.exception))

    def test_max_relation_fetches_raises(self) -> None:
        def fake_urlopen(req: object, timeout: float = 0) -> _FakeResponse:
            del req, timeout  # Unused.
            return _FakeResponse(_MINIMAL_OSM)

        osm_client = client.OsmApiClient(
            urlopen=fake_urlopen,
            min_request_interval_seconds=0,
            max_relation_fetches=1,
        )
        osm_client.fetch_relation_full(1)
        with self.assertRaises(client.OsmClientError) as ctx:
            osm_client.fetch_relation_full(2)
        self.assertIn("max relation fetches", str(ctx.exception))

    def test_throttle_sleeps_between_requests(self) -> None:
        clock = _FakeClock()

        def fake_urlopen(req: object, timeout: float = 0) -> _FakeResponse:
            del req, timeout  # Unused.
            return _FakeResponse(_MINIMAL_OSM)

        osm_client = client.OsmApiClient(
            urlopen=fake_urlopen,
            min_request_interval_seconds=1.0,
            max_relation_fetches=5,
            sleep=clock.sleep,
            monotonic=clock.monotonic,
        )
        osm_client.fetch_relation_full(1)
        osm_client.fetch_relation_full(2)
        self.assertEqual(clock.sleeps, [1.0])

    def test_retry_after_429_then_success(self) -> None:
        clock = _FakeClock()
        calls = {"n": 0}

        def fake_urlopen(req: object, timeout: float = 0) -> _FakeResponse:
            del req, timeout  # Unused.
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib_error.HTTPError(
                    "http://example.test/relation/1/full",
                    429,
                    "Too Many Requests",
                    {"Retry-After": "2"},
                    None,
                )
            return _FakeResponse(_MINIMAL_OSM)

        osm_client = client.OsmApiClient(
            urlopen=fake_urlopen,
            min_request_interval_seconds=0,
            max_retries=3,
            max_relation_fetches=5,
            sleep=clock.sleep,
            monotonic=clock.monotonic,
        )
        store = osm_client.fetch_relation_full(1)
        self.assertIn(1, store.relations)
        self.assertIn(2.0, clock.sleeps)

    def test_persistent_429_exhausts_retries(self) -> None:
        clock = _FakeClock()

        def fake_urlopen(req: object, timeout: float = 0) -> _FakeResponse:
            del req, timeout  # Unused.
            raise urllib_error.HTTPError(
                "http://example.test/relation/1/full",
                429,
                "Too Many Requests",
                {},
                None,
            )

        osm_client = client.OsmApiClient(
            urlopen=fake_urlopen,
            min_request_interval_seconds=0,
            max_retries=2,
            max_relation_fetches=5,
            sleep=clock.sleep,
            monotonic=clock.monotonic,
        )
        with self.assertRaises(client.OsmClientError) as ctx:
            osm_client.fetch_relation_full(1)
        self.assertIn("HTTP 429", str(ctx.exception))
        # Attempts: initial + 2 retries => 2 backoff sleeps (1s, 2s).
        self.assertEqual(clock.sleeps, [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
