"""Module entry point: python -m boundarykit."""

from __future__ import annotations

import sys

from boundarykit import cli

if __name__ == "__main__":
    sys.exit(cli.main())
