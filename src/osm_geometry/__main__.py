"""Module entry point: python -m osm_geometry."""

from __future__ import annotations

import sys

from osm_geometry.cli import main

if __name__ == "__main__":
    sys.exit(main())
