from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from robot_pet.checksums import write_checksums
from scripts.build_release import build_release
from scripts.build_site import build_site
from tests.helpers import write_synthetic_pet


def make_webp_project(root: Path) -> Path:
    pet_dir = write_synthetic_pet(root / "pet")
    png_path = pet_dir / "spritesheet.png"
    webp_path = pet_dir / "spritesheet.webp"
    with Image.open(png_path) as opened:
        opened.save(webp_path, format="WEBP", lossless=True, method=6, exact=True)
    png_path.unlink()
    manifest_path = pet_dir / "pet.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["spritesheetPath"] = "spritesheet.webp"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_checksums(
        pet_dir,
        (Path("pet.json"), Path("spritesheet.webp")),
        pet_dir / "checksums.txt",
    )
    for filename in ("NOTICE.md", "ASSET_LICENSE.md", "LICENSE"):
        (root / filename).write_text(filename, encoding="utf-8")
    web = root / "web"
    web.mkdir()
    for filename in ("index.html", "site.css", "site.js"):
        (web / filename).write_text(filename, encoding="utf-8")
    return root


class BuildScriptTests(unittest.TestCase):
    def test_release_and_site_build_from_real_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="robot-build-test-") as temporary:
            root = make_webp_project(Path(temporary))
            release = build_release(root, root / "dist")
            package = Path(str(release["package"]))
            self.assertTrue(package.is_file())
            self.assertTrue((root / "dist" / "pet.json").is_file())
            self.assertTrue((root / "dist" / "spritesheet.webp").is_file())
            with zipfile.ZipFile(package) as archive:
                self.assertIn("ASSET_LICENSE.md", archive.namelist())
                self.assertIn("LICENSE-CODE-MIT.txt", archive.namelist())

            release_manifest = (root / "dist" / "release-manifest.json").read_text(
                encoding="utf-8"
            )
            self.assertNotIn(str(root), release_manifest)
            self.assertIn('"target": "pet"', release_manifest)

            site_result = build_site(root, root / "site")
            self.assertTrue(site_result["ok"])
            self.assertTrue((root / "site" / "assets" / "spritesheet.webp").is_file())
            validation = (root / "site" / "assets" / "validation.json").read_text(
                encoding="utf-8"
            )
            self.assertNotIn(str(root), validation)

            build_site(root, root / "site")
            self.assertTrue((root / "site" / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
