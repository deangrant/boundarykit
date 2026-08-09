"""Tests for CLI error handling."""

from __future__ import annotations

import unittest
from unittest import mock

from osm_geometry import cli


class CliMainTest(unittest.TestCase):
    """Tests cli.main exit behavior."""

    def test_uncaught_keyerror_returns_exit_code_1(self) -> None:
        fake_service = mock.Mock()
        fake_service.run.side_effect = KeyError("unexpected")
        with mock.patch.object(cli, "build_service", return_value=fake_service):
            code = cli.main(["100", "-f", "geojson"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
