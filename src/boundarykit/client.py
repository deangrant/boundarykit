"""OSM API client for fetching relation data."""

from __future__ import annotations

from collections.abc import Callable
import logging
import time
from typing import Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request
import xml.etree.ElementTree as ET

from boundarykit import __version__
from boundarykit import models

_LOG = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.openstreetmap.org/api/0.6"
_USER_AGENT = f"boundarykit/{__version__}"
_DEFAULT_MAX_RESPONSE_BYTES = 32 * 1024 * 1024
_DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 1.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_MAX_RELATION_FETCHES = 64
_READ_CHUNK_BYTES = 64 * 1024
_MAX_RETRY_SLEEP_SECONDS = 60.0
_RETRYABLE_STATUS_CODES = frozenset({429, 503})


class OsmClientError(Exception):
    """OSM API fetch or XML parse failure."""


class OsmApiClientProtocol(Protocol):
    """Fetches OSM elements for a relation."""

    def fetch_relation_full(self, relation_id: int) -> models.ElementStore:
        """Downloads a relation and its members into an element store."""


class OsmApiClient:
    """HTTP client for the OSM API 0.6 XML endpoints."""

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        user_agent: str = _USER_AGENT,
        timeout_seconds: float = 60.0,
        *,
        max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
        min_request_interval_seconds: float = (
            _DEFAULT_MIN_REQUEST_INTERVAL_SECONDS
        ),
        max_retries: int = _DEFAULT_MAX_RETRIES,
        max_relation_fetches: int = _DEFAULT_MAX_RELATION_FETCHES,
        urlopen: Callable[..., object] | None = None,
        sleep: Callable[[float], None] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        """Creates an OSM API client.

        Args:
            base_url: OSM API 0.6 base URL.
            user_agent: User-Agent header value.
            timeout_seconds: Per-request socket timeout.
            max_response_bytes: Maximum response body size to accept.
            min_request_interval_seconds: Minimum delay between requests.
            max_retries: Retries for HTTP 429/503 responses.
            max_relation_fetches: Maximum HTTP GETs for this client instance.
            urlopen: Optional urllib opener override (for tests).
            sleep: Optional sleep callback (for tests).
            monotonic: Optional clock callback (for tests).
        """
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._min_request_interval_seconds = min_request_interval_seconds
        self._max_retries = max_retries
        self._max_relation_fetches = max_relation_fetches
        self._urlopen = urlopen or urllib_request.urlopen
        self._sleep = sleep or time.sleep
        self._monotonic = monotonic or time.monotonic
        self._fetch_count = 0
        self._last_request_monotonic: float | None = None

    def fetch_relation_full(self, relation_id: int) -> models.ElementStore:
        """Downloads relation/{id}/full and parses the XML payload.

        Args:
            relation_id: OSM relation id.

        Returns:
            Parsed element store.

        Raises:
            OsmClientError: On HTTP, size, budget, or parse failure.
        """
        url = f"{self._base_url}/relation/{relation_id}/full"
        return self._fetch_store(url)

    def _fetch_store(self, url: str) -> models.ElementStore:
        if self._fetch_count >= self._max_relation_fetches:
            raise OsmClientError(
                f"Exceeded max relation fetches "
                f"({self._max_relation_fetches})"
            )
        self._fetch_count += 1
        _LOG.info("Fetching OSM data from %s", url)
        req = urllib_request.Request(
            url, headers={"User-Agent": self._user_agent}
        )
        payload = self._request_with_retries(req, url)
        return parse_osm_xml(payload)

    def _request_with_retries(
        self,
        req: urllib_request.Request,
        url: str,
    ) -> bytes:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                with self._urlopen(
                    req, timeout=self._timeout_seconds
                ) as response:
                    return _read_limited_body(
                        response, self._max_response_bytes
                    )
            except urllib_error.HTTPError as err:
                last_error = err
                if (
                    err.code not in _RETRYABLE_STATUS_CODES
                    or attempt >= self._max_retries
                ):
                    raise OsmClientError(
                        f"HTTP {err.code} fetching {url}: {err.reason}"
                    ) from err
                delay = _retry_delay_seconds(err, attempt)
                _LOG.warning(
                    "HTTP %s from %s; retrying in %.1fs (attempt %s/%s)",
                    err.code,
                    url,
                    delay,
                    attempt + 1,
                    self._max_retries,
                )
                self._sleep(delay)
            except urllib_error.URLError as err:
                raise OsmClientError(
                    f"Network error fetching {url}: {err}"
                ) from err
        raise OsmClientError(f"Failed fetching {url}: {last_error}")

    def _throttle(self) -> None:
        if self._min_request_interval_seconds <= 0:
            self._last_request_monotonic = self._monotonic()
            return
        now = self._monotonic()
        if self._last_request_monotonic is not None:
            elapsed = now - self._last_request_monotonic
            wait = self._min_request_interval_seconds - elapsed
            if wait > 0:
                self._sleep(wait)
                now = self._monotonic()
        self._last_request_monotonic = now


def _read_limited_body(response: object, max_bytes: int) -> bytes:
    """Reads a response body up to max_bytes.

    Args:
        response: urllib response (or test double) with headers/read.
        max_bytes: Maximum accepted payload size.

    Returns:
        Full response body.

    Raises:
        OsmClientError: If Content-Length or streamed size exceeds the cap.
    """
    headers = getattr(response, "headers", None)
    content_length = _content_length(headers)
    if content_length is not None and content_length > max_bytes:
        raise OsmClientError(
            f"OSM response Content-Length {content_length} exceeds "
            f"limit of {max_bytes} bytes"
        )

    chunks: list[bytes] = []
    total = 0
    read = getattr(response, "read")
    while True:
        chunk = read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise OsmClientError(
                f"OSM response exceeded limit of {max_bytes} bytes"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _content_length(headers: object | None) -> int | None:
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return None
    raw = getter("Content-Length")
    if raw is None:
        raw = getter("content-length")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _retry_delay_seconds(err: urllib_error.HTTPError, attempt: int) -> float:
    retry_after = err.headers.get("Retry-After") if err.headers else None
    if retry_after is not None:
        try:
            delay = float(retry_after)
            if delay >= 0:
                return min(delay, _MAX_RETRY_SLEEP_SECONDS)
        except (TypeError, ValueError):
            pass
    return min(float(2**attempt), _MAX_RETRY_SLEEP_SECONDS)


def parse_osm_xml(payload: bytes | str) -> models.ElementStore:
    """Parses OSM XML into an element store.

    Args:
        payload: Raw XML bytes or string.

    Returns:
        Populated element store.

    Raises:
        OsmClientError: If the XML is invalid.
    """
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as err:
        raise OsmClientError(f"Invalid OSM XML: {err}") from err

    store = models.ElementStore()
    for element in root:
        tag = element.tag
        if tag == "node":
            node = _parse_node(element)
            store.nodes[node.osm_id] = node
        elif tag == "way":
            way = _parse_way(element)
            store.ways[way.osm_id] = way
        elif tag == "relation":
            relation = _parse_relation(element)
            store.relations[relation.osm_id] = relation
    return store


def _parse_node(element: ET.Element) -> models.OsmNode:
    try:
        osm_id = int(element.attrib["id"])
        lat = float(element.attrib["lat"])
        lon = float(element.attrib["lon"])
    except (KeyError, TypeError, ValueError) as err:
        raise _invalid_element_error("node", element, err) from err
    return models.OsmNode(
        osm_id=osm_id, coordinate=models.LatLon(lat=lat, lon=lon)
    )


def _parse_way(element: ET.Element) -> models.OsmWay:
    try:
        osm_id = int(element.attrib["id"])
        node_ids = [int(nd.attrib["ref"]) for nd in element.findall("nd")]
    except (KeyError, TypeError, ValueError) as err:
        raise _invalid_element_error("way", element, err) from err
    tags = _parse_tags(element)
    return models.OsmWay(osm_id=osm_id, node_ids=node_ids, tags=tags)


def _parse_relation(element: ET.Element) -> models.OsmRelation:
    try:
        osm_id = int(element.attrib["id"])
        members = [
            models.OsmMember(
                member_type=member.attrib["type"],
                ref=int(member.attrib["ref"]),
                role=member.attrib.get("role", ""),
            )
            for member in element.findall("member")
        ]
    except (KeyError, TypeError, ValueError) as err:
        raise _invalid_element_error("relation", element, err) from err
    tags = _parse_tags(element)
    return models.OsmRelation(osm_id=osm_id, members=members, tags=tags)


def _parse_tags(element: ET.Element) -> dict[str, str]:
    """Returns OSM tag key/value pairs from an element."""
    return {
        tag.attrib["k"]: tag.attrib["v"]
        for tag in element.findall("tag")
        if "k" in tag.attrib and "v" in tag.attrib
    }


def _invalid_element_error(
    kind: str,
    element: ET.Element,
    err: Exception,
) -> OsmClientError:
    """Builds OsmClientError for a malformed OSM XML element."""
    element_id = element.attrib.get("id")
    if isinstance(err, KeyError):
        detail = f"missing {err.args[0]}"
    else:
        detail = str(err) or err.__class__.__name__
    if element_id is not None:
        return OsmClientError(
            f"Invalid {kind} element id={element_id}: {detail}"
        )
    return OsmClientError(f"Invalid {kind} element: {detail}")
