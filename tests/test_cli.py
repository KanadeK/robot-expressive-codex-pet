from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from robot_pet.cli import _emit, build_parser, main
from tests.helpers import write_synthetic_pet


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="robot-cli-test-")
        self.root = Path(self._temp.name)
        self.pet_dir = write_synthetic_pet(self.root / "pet")
        self.pets_root = self.root / "installed"
        self.backups_root = self.root / "backups"

    def tearDown(self) -> None:
        self._temp.cleanup()

    def run_cli(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            return_code = main(arguments)
        return return_code, stdout.getvalue(), stderr.getvalue()

    def test_complete_command_cycle(self) -> None:
        code, output, _ = self.run_cli(["validate", str(self.pet_dir), "--json"])
        self.assertEqual(code, 0)
        self.assertIn('"ok": true', output)

        preview_dir = self.root / "previews"
        code, output, _ = self.run_cli(
            ["preview", str(self.pet_dir), "--output", str(preview_dir), "--json"]
        )
        self.assertEqual(code, 0)
        self.assertIn('"generated"', output)

        for name in ("NOTICE.md", "ASSET_LICENSE.md", "LICENSE"):
            (self.root / name).write_text(name, encoding="utf-8")
        package_path = self.root / "pet.zip"
        code, output, _ = self.run_cli(
            [
                "pack",
                str(self.pet_dir),
                "--output",
                str(package_path),
                "--project-root",
                str(self.root),
                "--json",
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(package_path.is_file())
        self.assertIn('"sha256"', output)

        code, output, _ = self.run_cli(
            [
                "install",
                str(package_path),
                "--pets-root",
                str(self.pets_root),
                "--backup-root",
                str(self.backups_root),
                "--json",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn('"action": "install"', output)

        code, output, _ = self.run_cli(
            ["doctor", "--pets-root", str(self.pets_root), "--json"]
        )
        self.assertEqual(code, 0)
        self.assertIn('"installed": true', output)

        code, output, _ = self.run_cli(
            [
                "uninstall",
                "--pets-root",
                str(self.pets_root),
                "--backup-root",
                str(self.backups_root),
                "--json",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn('"action": "uninstall"', output)

        code, output, _ = self.run_cli(
            ["doctor", "--pets-root", str(self.pets_root)]
        )
        self.assertEqual(code, 1)
        self.assertIn("FAIL:", output)

    def test_text_output_and_error_path(self) -> None:
        code, output, _ = self.run_cli(["validate", str(self.pet_dir)])
        self.assertEqual(code, 0)
        self.assertIn("PASS:", output)

        code, output, _ = self.run_cli(
            ["install", str(self.root / "missing"), "--json"]
        )
        self.assertEqual(code, 1)
        self.assertIn('"error": "FileNotFoundError"', output)

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _emit({"ok": True}, as_json=False)
        self.assertIn("'ok': True", buffer.getvalue())

    def test_version_action(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as raised:
            build_parser().parse_args(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("robot-pet 0.1.0", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
