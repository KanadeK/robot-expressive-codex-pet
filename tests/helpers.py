from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from robot_pet.checksums import write_checksums
from robot_pet.constants import ALL_ROWS, ATLAS_HEIGHT, ATLAS_WIDTH, CELL_HEIGHT, CELL_WIDTH


def refresh_checksums(pet_dir: Path) -> None:
    manifest = json.loads((pet_dir / "pet.json").read_text(encoding="utf-8"))
    write_checksums(
        pet_dir,
        (Path("pet.json"), Path(manifest["spritesheetPath"])),
        pet_dir / "checksums.txt",
    )


def write_synthetic_pet(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "robot-expressive",
        "displayName": "RobotExpressive / 表情机器人",
        "description": "Synthetic test fixture for the RobotExpressive pet toolchain.",
        "spriteVersionNumber": 2,
        "spritesheetPath": "spritesheet.png",
    }
    (root / "pet.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    atlas = Image.new("RGBA", (ATLAS_WIDTH, ATLAS_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(atlas)
    for row in ALL_ROWS:
        for column in range(row.frames):
            left = column * CELL_WIDTH + 36
            top = row.row * CELL_HEIGHT + 28
            color = (
                80 + (row.row * 11) % 160,
                30 + (column * 19) % 180,
                170,
                255,
            )
            draw.rounded_rectangle(
                (left, top, left + 118, top + 148),
                radius=18,
                fill=color,
            )
    atlas.save(root / "spritesheet.png", optimize=True)
    refresh_checksums(root)
    return root
