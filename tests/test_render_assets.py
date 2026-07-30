from __future__ import annotations

import hashlib
import json
import struct
import unittest
from pathlib import Path

from robot_pet.atlas import validate_pet_directory
from robot_pet.checksums import sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL = PROJECT_ROOT / "artwork" / "source" / "RobotExpressive.glb"
EXPECTED_MODEL_SHA256 = "047f5e5fb3bb6d378bd1df16ca6137f2a596c99b3a1b5690b4020c05aaf6f319"
EXPECTED_CLIPS = {
    "Dance",
    "Death",
    "Idle",
    "Jump",
    "No",
    "Punch",
    "Running",
    "Sitting",
    "Standing",
    "ThumbsUp",
    "Walking",
    "WalkJump",
    "Wave",
    "Yes",
}


def read_glb_json(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    magic, version, total_length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2 or total_length != len(data):
        raise ValueError("invalid GLB 2.0 header")
    offset = 12
    while offset < len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            parsed = json.loads(chunk.rstrip(b" \x00").decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("GLB JSON chunk is not an object")
            return parsed
    raise ValueError("GLB JSON chunk not found")


class RenderAssetTests(unittest.TestCase):
    def test_pinned_model_hash_and_animation_vocabulary(self) -> None:
        self.assertEqual(hashlib.sha256(MODEL.read_bytes()).hexdigest(), EXPECTED_MODEL_SHA256)
        gltf = read_glb_json(MODEL)
        animations = gltf.get("animations")
        self.assertIsInstance(animations, list)
        names = {animation["name"] for animation in animations if isinstance(animation, dict)}
        self.assertEqual(names, EXPECTED_CLIPS)

    def test_render_dependencies_are_exactly_pinned(self) -> None:
        package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["packageManager"], "pnpm@11.9.0")
        self.assertEqual(package["dependencies"]["three"], "0.185.1")
        self.assertEqual(package["dependencies"]["playwright"], "1.62.0")
        self.assertNotRegex(package["dependencies"]["three"], r"[\^~*xX]")
        self.assertNotRegex(package["dependencies"]["playwright"], r"[\^~*xX]")

    def test_provenance_and_shipped_atlas_agree(self) -> None:
        provenance = json.loads(
            (PROJECT_ROOT / "artwork" / "PROVENANCE.json").read_text(encoding="utf-8")
        )
        render = json.loads(
            (PROJECT_ROOT / "artwork" / "RENDER_REPORT.json").read_text(encoding="utf-8")
        )
        self.assertTrue(provenance["character"]["existing_character"])
        self.assertFalse(provenance["render"]["generative_ai_used"])
        self.assertEqual(provenance["source"]["sha256"], EXPECTED_MODEL_SHA256)
        self.assertEqual(render["source"]["modelSha256"], EXPECTED_MODEL_SHA256)
        self.assertEqual(
            render["source"]["upstreamCommit"],
            provenance["source"]["commit"],
        )
        sprite = PROJECT_ROOT / "pet" / "spritesheet.webp"
        self.assertEqual(render["atlas"]["sha256"], sha256_file(sprite))
        self.assertEqual(render["atlas"]["populatedCells"], 73)
        self.assertTrue(render["atlas"]["validationOk"])

    def test_shipped_pet_passes_full_validator(self) -> None:
        report = validate_pet_directory(PROJECT_ROOT / "pet")
        self.assertTrue(report.ok, report.format_text())
        self.assertEqual(report.warning_count, 0, report.format_text())


if __name__ == "__main__":
    unittest.main()
