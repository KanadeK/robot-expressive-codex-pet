from __future__ import annotations

import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from robot_pet.checksums import sha256_file
from robot_pet.packaging import ZIP_TIMESTAMP, build_deterministic_package
from tests.helpers import write_synthetic_pet


class PackagingTests(unittest.TestCase):
    def test_packages_are_identical_across_separated_runs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="robot-package-test-") as temporary:
            root = Path(temporary)
            pet_dir = write_synthetic_pet(root / "pet")
            first = root / "first.zip"
            second = root / "second.zip"
            build_deterministic_package(pet_dir, first)
            time.sleep(1.1)
            build_deterministic_package(pet_dir, second)
            self.assertEqual(sha256_file(first), sha256_file(second))
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    {item.date_time for item in archive.infolist()},
                    {ZIP_TIMESTAMP},
                )
                self.assertEqual(
                    set(archive.namelist()),
                    {"checksums.txt", "pet.json", "spritesheet.png"},
                )

    def test_missing_extra_and_duplicate_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="robot-package-test-") as temporary:
            root = Path(temporary)
            pet_dir = write_synthetic_pet(root / "pet")
            with self.assertRaises(FileNotFoundError):
                build_deterministic_package(
                    pet_dir,
                    root / "missing.zip",
                    extra_files=[(root / "absent", "NOTICE.md")],
                )
            notice = root / "NOTICE.md"
            notice.write_text("notice", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate archive paths"):
                build_deterministic_package(
                    pet_dir,
                    root / "duplicate.zip",
                    extra_files=[(notice, "pet.json")],
                )

    def test_invalid_pet_is_not_packaged(self) -> None:
        with tempfile.TemporaryDirectory(prefix="robot-package-test-") as temporary:
            root = Path(temporary)
            pet_dir = write_synthetic_pet(root / "pet")
            (pet_dir / "spritesheet.png").unlink()
            with self.assertRaisesRegex(ValueError, "FAIL:"):
                build_deterministic_package(pet_dir, root / "invalid.zip")


if __name__ == "__main__":
    unittest.main()
