"""OSM API client for fetching relation data."""

from __future__ import annotations

import logging
from typing import Protocol
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen
import xml.etree.ElementTree as Et

from osm_geometry.models import ElementStore
from osm_geometry.models import LatLon
from osm_geometry.models import OsmMember
from osm_geometry.models import OsmNode
from osm_geometry.models import OsmRelation
from osm_geometry.models import OsmWay

_LOG = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.openstreetmap.org/api/0.6"
_USER_AGENT = "osm-geometry/0.1"


class OsmClientError(Exception):
    """Raised when the OSM API cannot be fetched or parsed."""


class OsmApiClientProtocol(Protocol):
    """Fetches OSM elements for a relation."""

    def fetch_relation_full(self, relation_id: int) -> ElementStore:
        """Downloads a relation and its members into an element store."""


class OsmApiClient:
    """HTTP client for the OSM API 0.6 XML endpoints."""

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        user_agent: str = _USER_AGENT,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._timeout_seconds = timeout_seconds

    def fetch_relation_full(self, relation_id: int) -> ElementStore:
        """Downloads relation/{id}/full and parses the XML payload.

        Args:
            relation_id: OSM relation id.

        Returns:
            Parsed element store.

        Raises:
            OsmClientError: On HTTP or parse failure.
        """
        url = f"{self._base_url}/relation/{relation_id}/full"
        return self._fetch_store(url)

    def fetch_relation(self, relation_id: int) -> ElementStore:
        """Downloads a bare relation document (no members expanded).

        Args:
            relation_id: OSM relation id.

        Returns:
            Parsed element store.

        Raises:
            OsmClientError: On HTTP or parse failure.
        """
        url = f"{self._base_url}/relation/{relation_id}"
        return self._fetch_store(url)

    def _fetch_store(self, url: str) -> ElementStore:
        _LOG.info("Fetching OSM data from %s", url)
        request = Request(url, headers={"User-Agent": self._user_agent})
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = response.read()
        except HTTPError as error:
            raise OsmClientError(
                f"HTTP {error.code} fetching {url}: {error.reason}"
            ) from error
        except URLError as error:
            raise OsmClientError(
                f"Network error fetching {url}: {error}"
            ) from error
        return parse_osm_xml(payload)


def parse_osm_xml(payload: bytes | str) -> ElementStore:
    """Parses OSM XML into an element store.

    Args:
        payload: Raw XML bytes or string.

    Returns:
        Populated element store.

    Raises:
        OsmClientError: If the XML is invalid.
    """
    try:
        root = Et.fromstring(payload)
    except Et.ParseError as error:
        raise OsmClientError(f"Invalid OSM XML: {error}") from error

    store = ElementStore()
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


def _parse_node(element: Et.Element) -> OsmNode:
    osm_id = int(element.attrib["id"])
    lat = float(element.attrib["lat"])
    lon = float(element.attrib["lon"])
    return OsmNode(osm_id=osm_id, coordinate=LatLon(lat=lat, lon=lon))


def _parse_way(element: Et.Element) -> OsmWay:
    osm_id = int(element.attrib["id"])
    node_ids = [int(nd.attrib["ref"]) for nd in element.findall("nd")]
    tags = {
        tag.attrib["k"]: tag.attrib["v"]
        for tag in element.findall("tag")
        if "k" in tag.attrib and "v" in tag.attrib
    }
    return OsmWay(osm_id=osm_id, node_ids=node_ids, tags=tags)


def _parse_relation(element: Et.Element) -> OsmRelation:
    osm_id = int(element.attrib["id"])
    members = [
        OsmMember(
            member_type=member.attrib["type"],
            ref=int(member.attrib["ref"]),
            role=member.attrib.get("role", ""),
        )
        for member in element.findall("member")
    ]
    tags = {
        tag.attrib["k"]: tag.attrib["v"]
        for tag in element.findall("tag")
        if "k" in tag.attrib and "v" in tag.attrib
    }
    return OsmRelation(osm_id=osm_id, members=members, tags=tags)
