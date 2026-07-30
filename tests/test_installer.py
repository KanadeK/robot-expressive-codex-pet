from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from robot_pet.installer import doctor, install_pet, safe_extract_zip, uninstall_pet
from robot_pet.packaging import build_deterministic_package
from tests.helpers import write_synthetic_pet


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="robot-installer-test-")
        self.root = Path(self._temp.name)
        self.source = write_synthetic_pet(self.root / "source")
        self.pets_root = self.root / "pets"
        self.backup_root = self.root / "backups"

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_install_doctor_backup_and_recoverable_uninstall(self) -> None:
        first = install_pet(
            self.source,
            pets_root=self.pets_root,
            backup_root=self.backup_root,
        )
        self.assertTrue(first.ok)
        destination = self.pets_root / "robot-expressive"
        (destination / "user-note.txt").write_text("keep me", encoding="utf-8")
        second = install_pet(
            self.source,
            pets_root=self.pets_root,
            backup_root=self.backup_root,
        )
        self.assertIsNotNone(second.backup)
        backup = Path(second.backup or "")
        self.assertEqual(backup.joinpath("user-note.txt").read_text(), "keep me")
        self.assertTrue(doctor("robot-expressive", pets_root=self.pets_root)["ok"])
        removed = uninstall_pet(
            "robot-expressive",
            pets_root=self.pets_root,
            backup_root=self.backup_root,
        )
        self.assertFalse(destination.exists())
        self.assertTrue(Path(removed.backup or "").is_dir())

    def test_zip_slip_member_is_rejected(self) -> None:
        archive = self.root / "malicious.zip"
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr("../escape.txt", "no")
        with self.assertRaisesRegex(ValueError, "unsafe archive member"):
            safe_extract_zip(archive, self.root / "extract")
        self.assertFalse((self.root / "escape.txt").exists())

    def test_install_from_zip_and_missing_doctor(self) -> None:
        archive = self.root / "pet.zip"
        build_deterministic_package(self.source, archive)
        result = install_pet(
            archive,
            pets_root=self.pets_root,
            backup_root=self.backup_root,
        )
        self.assertTrue(result.ok)
        missing = doctor("absent", pets_root=self.pets_root)
        self.assertFalse(missing["ok"])
        self.assertFalse(missing["installed"])

    def test_safe_extract_handles_directories(self) -> None:
        archive = self.root / "nested.zip"
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr("folder/", "")
            handle.writestr("folder/file.txt", "safe")
        destination = self.root / "nested"
        safe_extract_zip(archive, destination)
        self.assertEqual((destination / "folder" / "file.txt").read_text(), "safe")

    def test_install_failure_restores_existing_destination(self) -> None:
        install_pet(
            self.source,
            pets_root=self.pets_root,
            backup_root=self.backup_root,
        )
        destination = self.pets_root / "robot-expressive"
        (destination / "user-note.txt").write_text("restore me", encoding="utf-8")
        with (
            patch("robot_pet.installer.os.replace", side_effect=OSError("simulated")),
            self.assertRaisesRegex(OSError, "simulated"),
        ):
            install_pet(
                self.source,
                pets_root=self.pets_root,
                backup_root=self.backup_root,
            )
        self.assertEqual((destination / "user-note.txt").read_text(), "restore me")
        staging_exists = any(
            path.name.startswith(".robot-expressive.staging")
            for path in self.pets_root.iterdir()
        )
        self.assertFalse(staging_exists)

    def test_missing_sources_and_uninstall_are_rejected(self) -> None:
        with self.assertRaises(FileNotFoundError):
            install_pet(
                self.root / "missing",
                pets_root=self.pets_root,
                backup_root=self.backup_root,
            )
        with self.assertRaises(FileNotFoundError):
            uninstall_pet(
                "robot-expressive",
                pets_root=self.pets_root,
                backup_root=self.backup_root,
            )


if __name__ == "__main__":
    unittest.main()
