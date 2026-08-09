"""OSM API client for fetching relation data."""

from __future__ import annotations

import logging
from typing import Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request
import xml.etree.ElementTree as ET

from osm_geometry import models

_LOG = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.openstreetmap.org/api/0.6"
_USER_AGENT = "osm-geometry/0.1"


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
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._timeout_seconds = timeout_seconds

    def fetch_relation_full(self, relation_id: int) -> models.ElementStore:
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

    def fetch_relation(self, relation_id: int) -> models.ElementStore:
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

    def _fetch_store(self, url: str) -> models.ElementStore:
        _LOG.info("Fetching OSM data from %s", url)
        req = urllib_request.Request(
            url, headers={"User-Agent": self._user_agent}
        )
        try:
            with urllib_request.urlopen(
                req, timeout=self._timeout_seconds
            ) as response:
                payload = response.read()
        except urllib_error.HTTPError as err:
            raise OsmClientError(
                f"HTTP {err.code} fetching {url}: {err.reason}"
            ) from err
        except urllib_error.URLError as err:
            raise OsmClientError(
                f"Network error fetching {url}: {err}"
            ) from err
        return parse_osm_xml(payload)


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
    osm_id = int(element.attrib["id"])
    lat = float(element.attrib["lat"])
    lon = float(element.attrib["lon"])
    return models.OsmNode(
        osm_id=osm_id, coordinate=models.LatLon(lat=lat, lon=lon)
    )


def _parse_way(element: ET.Element) -> models.OsmWay:
    osm_id = int(element.attrib["id"])
    node_ids = [int(nd.attrib["ref"]) for nd in element.findall("nd")]
    tags = {
        tag.attrib["k"]: tag.attrib["v"]
        for tag in element.findall("tag")
        if "k" in tag.attrib and "v" in tag.attrib
    }
    return models.OsmWay(osm_id=osm_id, node_ids=node_ids, tags=tags)


def _parse_relation(element: ET.Element) -> models.OsmRelation:
    osm_id = int(element.attrib["id"])
    members = [
        models.OsmMember(
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
    return models.OsmRelation(osm_id=osm_id, members=members, tags=tags)
