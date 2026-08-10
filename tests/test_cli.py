"""Tests for CLI error handling and argv-driven exit codes."""

from __future__ import annotations

import io
import pathlib
import unittest
from unittest import mock

from boundarykit import assembler
from boundarykit import cli


class CliMainTest(unittest.TestCase):
    """Tests cli.main exit behavior."""

    def test_uncaught_keyerror_propagates(self) -> None:
        fake_service = mock.Mock()
        fake_service.run.side_effect = KeyError("unexpected")
        with mock.patch.object(cli, "build_service", return_value=fake_service):
            with self.assertRaises(KeyError):
                cli.main(["100", "-f", "geojson"])

    def test_success_prints_paths_and_exits_0(self) -> None:
        fake_service = mock.Mock()
        fake_service.run.return_value = [
            pathlib.Path("/tmp/out.geojson"),
            pathlib.Path("/tmp/out.wkt"),
        ]
        stdout = io.StringIO()
        with mock.patch.object(cli, "build_service", return_value=fake_service):
            with mock.patch("sys.stdout", stdout):
                code = cli.main(
                    ["100", "-f", "geojson,wkt", "--output-dir", "/tmp"]
                )
        self.assertEqual(code, 0)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            ["/tmp/out.geojson", "/tmp/out.wkt"],
        )
        fake_service.run.assert_called_once()

    def test_empty_geometry_returns_exit_code_1(self) -> None:
        fake_service = mock.Mock()
        fake_service.run.side_effect = assembler.AssemblyError(
            "Relation 100 produced no polygon geometry"
        )
        with mock.patch.object(cli, "build_service", return_value=fake_service):
            code = cli.main(["100", "-f", "geojson"])
        self.assertEqual(code, 1)

    def test_empty_format_flag_returns_exit_code_1(self) -> None:
        fake_service = mock.Mock()
        fake_service.run.side_effect = ValueError(
            "At least one export format is required"
        )
        with mock.patch.object(cli, "build_service", return_value=fake_service):
            code = cli.main(["100", "-f", " , "])
        self.assertEqual(code, 1)
        self.assertEqual(fake_service.run.call_args.args[1], [])

    def test_output_with_multiple_formats_errors(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main(
                [
                    "100",
                    "-f",
                    "geojson,wkt",
                    "--output",
                    "/tmp/out.geojson",
                ]
            )
        self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
