"""Deterministic contact sheets and animation previews from a validated atlas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw, ImageFont

from .atlas import validate_pet_directory
from .constants import (
    ALL_ROWS,
    CELL_HEIGHT,
    CELL_WIDTH,
    LOOK_DIRECTIONS,
    STANDARD_ROWS,
)

PREVIEW_SCALE = 2
PREVIEW_BACKGROUND = (17, 24, 39, 255)


def _manifest(pet_dir: Path) -> dict[str, object]:
    parsed = json.loads((pet_dir / "pet.json").read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("pet.json must contain an object")
    return cast(dict[str, object], parsed)


def _load_atlas(pet_dir: Path) -> Image.Image:
    manifest = _manifest(pet_dir)
    sprite_name = manifest["spritesheetPath"]
    if not isinstance(sprite_name, str):
        raise ValueError("invalid spritesheetPath")
    with Image.open(pet_dir / sprite_name) as opened:
        return opened.convert("RGBA")


def _cell(atlas: Image.Image, row: int, column: int) -> Image.Image:
    left = column * CELL_WIDTH
    top = row * CELL_HEIGHT
    return atlas.crop((left, top, left + CELL_WIDTH, top + CELL_HEIGHT))


def _composite_for_preview(frame: Image.Image) -> Image.Image:
    background = Image.new("RGBA", frame.size, PREVIEW_BACKGROUND)
    background.alpha_composite(frame)
    return background.resize(
        (CELL_WIDTH * PREVIEW_SCALE, CELL_HEIGHT * PREVIEW_SCALE),
        Image.Resampling.NEAREST,
    )


def render_previews(pet_dir: Path | str, output_dir: Path | str) -> dict[str, object]:
    source = Path(pet_dir).resolve()
    destination = Path(output_dir).resolve()
    report = validate_pet_directory(source)
    if not report.ok:
        raise ValueError(report.format_text())
    destination.mkdir(parents=True, exist_ok=True)
    atlas = _load_atlas(source)
    generated: list[str] = []
    for row in STANDARD_ROWS:
        frames = [
            _composite_for_preview(_cell(atlas, row.row, index))
            for index in range(row.frames)
        ]
        durations = [row.duration_for(index) for index in range(row.frames)]
        gif_path = destination / f"{row.name}.gif"
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            disposal=2,
        )
        png_path = destination / f"{row.name}.png"
        frames[0].save(png_path)
        generated.extend([str(gif_path), str(png_path)])
    look_frames = [
        _composite_for_preview(_cell(atlas, 9 + index // 8, index % 8))
        for index in range(16)
    ]
    look_path = destination / "look-directions.gif"
    look_frames[0].save(
        look_path,
        save_all=True,
        append_images=look_frames[1:],
        duration=[150] * 16,
        loop=0,
        disposal=2,
    )
    generated.append(str(look_path))
    contact_path = destination / "contact-sheet.png"
    _render_contact_sheet(atlas, contact_path)
    generated.append(str(contact_path))
    return {"ok": True, "output_dir": str(destination), "generated": generated}


def _render_contact_sheet(atlas: Image.Image, output: Path) -> None:
    label_width = 154
    scale = 0.5
    cell_width = int(CELL_WIDTH * scale)
    cell_height = int(CELL_HEIGHT * scale)
    margin = 16
    header_height = 34
    width = margin * 2 + label_width + cell_width * 8
    height = margin * 2 + header_height + cell_height * len(ALL_ROWS)
    canvas = Image.new("RGBA", (width, height), (10, 15, 25, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for column in range(8):
        x = margin + label_width + column * cell_width + 4
        draw.text((x, margin + 8), str(column), fill=(148, 163, 184, 255), font=font)
    for row_spec in ALL_ROWS:
        y = margin + header_height + row_spec.row * cell_height
        label = row_spec.name
        draw.text((margin, y + 8), label, fill=(226, 232, 240, 255), font=font)
        if row_spec.row >= 9:
            offset = (row_spec.row - 9) * 8
            draw.text(
                (margin, y + 24),
                f"{LOOK_DIRECTIONS[offset]}..{LOOK_DIRECTIONS[offset + 7]}",
                fill=(148, 163, 184, 255),
                font=font,
            )
        for column in range(8):
            x = margin + label_width + column * cell_width
            dark = (24, 33, 48, 255) if (row_spec.row + column) % 2 else (31, 41, 55, 255)
            draw.rectangle((x, y, x + cell_width - 1, y + cell_height - 1), fill=dark)
            frame = _cell(atlas, row_spec.row, column).resize(
                (cell_width, cell_height), Image.Resampling.LANCZOS
            )
            canvas.alpha_composite(frame, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, optimize=True)
