from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from robot_pet.preview import render_previews
from tests.helpers import write_synthetic_pet


class PreviewTests(unittest.TestCase):
    def test_preview_generation_uses_real_atlas_cells(self) -> None:
        with tempfile.TemporaryDirectory(prefix="robot-preview-test-") as temporary:
            root = Path(temporary)
            pet_dir = write_synthetic_pet(root / "pet")
            output = root / "previews"
            result = render_previews(pet_dir, output)
            self.assertTrue(result["ok"])
            self.assertTrue((output / "idle.gif").is_file())
            self.assertTrue((output / "look-directions.gif").is_file())
            with Image.open(output / "contact-sheet.png") as contact:
                self.assertGreater(contact.width, 800)
                self.assertGreater(contact.height, 1000)


if __name__ == "__main__":
    unittest.main()
