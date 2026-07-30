from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from robot_pet.atlas import validate_pet_directory
from robot_pet.constants import CELL_HEIGHT, CELL_WIDTH
from tests.helpers import refresh_checksums, write_synthetic_pet


class AtlasValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._base_temp = tempfile.TemporaryDirectory(prefix="robot-atlas-base-")
        cls.base = write_synthetic_pet(Path(cls._base_temp.name) / "pet")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._base_temp.cleanup()

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="robot-atlas-test-")
        self.pet_dir = Path(self._temp.name) / "pet"
        shutil.copytree(self.base, self.pet_dir)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def issue_codes(self) -> set[str]:
        return {issue.code for issue in validate_pet_directory(self.pet_dir).issues}

    def test_valid_v2_fixture_passes(self) -> None:
        report = validate_pet_directory(self.pet_dir)
        self.assertTrue(report.ok, report.format_text())
        self.assertEqual(report.metadata["atlas_width"], 1536)
        self.assertEqual(report.metadata["atlas_height"], 2288)

    def test_required_cell_cannot_be_blank(self) -> None:
        path = self.pet_dir / "spritesheet.png"
        with Image.open(path) as opened:
            atlas = opened.convert("RGBA")
        atlas.paste((0, 0, 0, 0), (0, 3 * CELL_HEIGHT, CELL_WIDTH, 4 * CELL_HEIGHT))
        atlas.save(path)
        refresh_checksums(self.pet_dir)
        self.assertIn("atlas.used_cell_empty", self.issue_codes())

    def test_unused_cell_must_be_transparent(self) -> None:
        path = self.pet_dir / "spritesheet.png"
        with Image.open(path) as opened:
            atlas = opened.convert("RGBA")
        atlas.putpixel((7 * CELL_WIDTH + 50, 50), (255, 0, 0, 255))
        atlas.save(path)
        refresh_checksums(self.pet_dir)
        self.assertIn("atlas.unused_cell_populated", self.issue_codes())

    def test_wrong_dimensions_fail(self) -> None:
        path = self.pet_dir / "spritesheet.png"
        Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(path)
        refresh_checksums(self.pet_dir)
        self.assertIn("atlas.dimensions", self.issue_codes())

    def test_v1_manifest_is_rejected(self) -> None:
        manifest_path = self.pet_dir / "pet.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["spriteVersionNumber"] = 1
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        refresh_checksums(self.pet_dir)
        self.assertIn("manifest.sprite_version", self.issue_codes())

    def test_checksum_mismatch_is_rejected(self) -> None:
        manifest_path = self.pet_dir / "pet.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["description"] = "Changed after checksums were written."
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.assertIn("checksums.mismatch", self.issue_codes())

    def test_missing_directory_and_manifest_are_rejected(self) -> None:
        missing = validate_pet_directory(self.pet_dir / "absent")
        self.assertIn("pet.not_directory", {issue.code for issue in missing.issues})
        (self.pet_dir / "pet.json").unlink()
        self.assertIn("manifest.missing", self.issue_codes())

    def test_invalid_manifest_shapes_are_rejected(self) -> None:
        manifest_path = self.pet_dir / "pet.json"
        manifest_path.write_text("{", encoding="utf-8")
        self.assertIn("manifest.invalid_json", self.issue_codes())
        manifest_path.write_text("[]\n", encoding="utf-8")
        self.assertIn("manifest.not_object", self.issue_codes())
        manifest_path.write_text("{}\n", encoding="utf-8")
        codes = self.issue_codes()
        self.assertIn("manifest.missing_field", codes)
        self.assertIn("manifest.invalid_id", codes)

    def test_unsafe_and_missing_sprite_paths_are_rejected(self) -> None:
        manifest_path = self.pet_dir / "pet.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["spritesheetPath"] = "../escape.png"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertIn("manifest.unsafe_sprite_path", self.issue_codes())

        manifest["spritesheetPath"] = "missing.png"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertIn("atlas.missing", self.issue_codes())

    def test_unreadable_wrong_format_and_mode_are_rejected(self) -> None:
        sprite = self.pet_dir / "spritesheet.png"
        sprite.write_text("not an image", encoding="utf-8")
        refresh_checksums(self.pet_dir)
        self.assertIn("atlas.unreadable", self.issue_codes())

        Image.new("RGB", (1536, 2288), (255, 255, 255)).save(sprite, format="BMP")
        refresh_checksums(self.pet_dir)
        codes = self.issue_codes()
        self.assertIn("atlas.format", codes)
        self.assertIn("atlas.mode", codes)

    def test_checksum_file_failures_are_reported(self) -> None:
        checksum_path = self.pet_dir / "checksums.txt"
        checksum_path.unlink()
        report = validate_pet_directory(self.pet_dir)
        self.assertIn("checksums.missing", {issue.code for issue in report.issues})

        checksum_path.write_text("# empty\n", encoding="utf-8")
        self.assertIn("checksums.empty", self.issue_codes())

        checksum_path.write_text(f"{'0' * 64}  absent.bin\n", encoding="utf-8")
        self.assertIn("checksums.file_missing", self.issue_codes())


if __name__ == "__main__":
    unittest.main()
