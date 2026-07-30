"""Strict validation for Codex v2 pet directories."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, UnidentifiedImageError

from .checksums import parse_checksums, sha256_file
from .constants import (
    ALL_ROWS,
    ATLAS_HEIGHT,
    ATLAS_WIDTH,
    CELL_HEIGHT,
    CELL_WIDTH,
    MAX_UPLOAD_BYTES,
    REQUIRED_MANIFEST_FIELDS,
    SPRITE_VERSION,
)
from .report import ValidationReport

PET_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _read_manifest(pet_dir: Path, report: ValidationReport) -> dict[str, Any] | None:
    manifest_path = pet_dir / "pet.json"
    if not manifest_path.is_file():
        report.add("error", "manifest.missing", "pet.json does not exist", "pet.json")
        return None
    try:
        parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report.add("error", "manifest.invalid_json", str(exc), "pet.json")
        return None
    if not isinstance(parsed, dict):
        report.add("error", "manifest.not_object", "pet.json must contain a JSON object")
        return None
    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in parsed:
            report.add("error", "manifest.missing_field", f"required field {field!r} is missing")
    pet_id = parsed.get("id")
    if not isinstance(pet_id, str) or not PET_ID_RE.fullmatch(pet_id):
        report.add(
            "error",
            "manifest.invalid_id",
            "id must be a lowercase kebab-case identifier",
            "pet.json:id",
        )
    for field in ("displayName", "description"):
        value = parsed.get(field)
        if not isinstance(value, str) or not value.strip():
            report.add("error", "manifest.invalid_text", f"{field} must be a non-empty string")
    if parsed.get("spriteVersionNumber") != SPRITE_VERSION:
        report.add(
            "error",
            "manifest.sprite_version",
            f"spriteVersionNumber must be {SPRITE_VERSION}",
            "pet.json:spriteVersionNumber",
        )
    return parsed


def _safe_sprite_path(manifest: dict[str, Any], report: ValidationReport) -> Path | None:
    raw_path = manifest.get("spritesheetPath")
    if not isinstance(raw_path, str) or not raw_path.strip():
        report.add("error", "manifest.invalid_sprite_path", "spritesheetPath must be a string")
        return None
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
        report.add(
            "error",
            "manifest.unsafe_sprite_path",
            "spritesheetPath must name one file inside the pet directory",
        )
        return None
    if path.suffix.lower() not in {".webp", ".png"}:
        report.add("error", "manifest.sprite_extension", "spritesheet must be PNG or WebP")
    return path


def _cell_box(row: int, column: int) -> tuple[int, int, int, int]:
    left = column * CELL_WIDTH
    top = row * CELL_HEIGHT
    return left, top, left + CELL_WIDTH, top + CELL_HEIGHT


def _edge_has_alpha(alpha: Image.Image) -> bool:
    width, height = alpha.size
    border = Image.new("L", alpha.size, 0)
    border.paste(255, (0, 0, width, 2))
    border.paste(255, (0, height - 2, width, height))
    border.paste(255, (0, 0, 2, height))
    border.paste(255, (width - 2, 0, width, height))
    return ImageChops.multiply(alpha, border).getbbox() is not None


def _validate_cells(image: Image.Image, report: ValidationReport) -> None:
    alpha = image.getchannel("A")
    coverage: dict[str, list[float]] = {}
    for row_spec in ALL_ROWS:
        row_coverage: list[float] = []
        for column in range(8):
            cell_alpha = alpha.crop(_cell_box(row_spec.row, column))
            bbox = cell_alpha.getbbox()
            nonzero = sum(cell_alpha.histogram()[1:])
            ratio = nonzero / (CELL_WIDTH * CELL_HEIGHT)
            row_coverage.append(round(ratio, 6))
            location = f"row={row_spec.row},column={column},state={row_spec.name}"
            if column < row_spec.frames:
                if bbox is None:
                    report.add(
                        "error",
                        "atlas.used_cell_empty",
                        "required animation cell is fully transparent",
                        location,
                    )
                elif ratio < 0.002:
                    report.add(
                        "warning",
                        "atlas.used_cell_tiny",
                        f"only {ratio:.3%} of the cell is visible",
                        location,
                    )
                if bbox is not None and _edge_has_alpha(cell_alpha):
                    report.add(
                        "warning",
                        "atlas.cell_touches_edge",
                        "visible pixels touch the two-pixel cell safety edge",
                        location,
                    )
            elif bbox is not None:
                report.add(
                    "error",
                    "atlas.unused_cell_populated",
                    "unused animation cell must be fully transparent",
                    location,
                )
        coverage[row_spec.name] = row_coverage
    report.metadata["cell_alpha_coverage"] = coverage


def _validate_hidden_rgb(image: Image.Image, report: ValidationReport) -> None:
    red, green, blue, alpha = image.split()
    rgb_max = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    transparent = alpha.point(lambda value: 255 if value == 0 else 0)
    hidden = ImageChops.multiply(rgb_max, transparent)
    if hidden.getbbox() is not None:
        report.add(
            "warning",
            "atlas.hidden_rgb",
            "fully transparent pixels retain RGB data; deterministic packages should clear it",
        )


def _validate_checksum_file(pet_dir: Path, report: ValidationReport) -> None:
    checksum_path = pet_dir / "checksums.txt"
    if not checksum_path.exists():
        report.add(
            "warning",
            "checksums.missing",
            "pet/checksums.txt is absent; release packaging should include it",
        )
        return
    try:
        entries = parse_checksums(checksum_path)
    except (OSError, UnicodeError, ValueError) as exc:
        report.add("error", "checksums.invalid", str(exc), "checksums.txt")
        return
    if not entries:
        report.add("error", "checksums.empty", "checksums.txt contains no file hashes")
        return
    for expected, relative in entries:
        candidate = pet_dir / relative
        if not candidate.is_file():
            report.add(
                "error",
                "checksums.file_missing",
                f"checksummed file is missing: {relative.as_posix()}",
            )
            continue
        actual = sha256_file(candidate)
        if actual != expected:
            report.add(
                "error",
                "checksums.mismatch",
                f"SHA-256 mismatch for {relative.as_posix()}",
            )
    report.metadata["checksummed_files"] = len(entries)


def validate_pet_directory(path: Path | str, *, verify_checksums: bool = True) -> ValidationReport:
    """Validate a directory containing pet.json and one Codex v2 atlas."""

    pet_dir = Path(path).expanduser().resolve()
    report = ValidationReport(pet_dir)
    if not pet_dir.is_dir():
        report.add("error", "pet.not_directory", "target is not a directory")
        return report
    manifest = _read_manifest(pet_dir, report)
    if manifest is None:
        return report
    sprite_relative = _safe_sprite_path(manifest, report)
    if sprite_relative is None:
        return report
    sprite_path = pet_dir / sprite_relative
    if not sprite_path.is_file():
        report.add(
            "error",
            "atlas.missing",
            f"spritesheet does not exist: {sprite_relative.as_posix()}",
        )
        return report
    sprite_size = sprite_path.stat().st_size
    report.metadata.update(
        {
            "pet_id": manifest.get("id"),
            "sprite_version_number": manifest.get("spriteVersionNumber"),
            "spritesheet": str(sprite_path),
            "spritesheet_bytes": sprite_size,
            "spritesheet_sha256": sha256_file(sprite_path),
        }
    )
    if sprite_size > MAX_UPLOAD_BYTES:
        report.add(
            "warning",
            "atlas.over_web_limit",
            f"spritesheet exceeds the documented 20 MiB web-upload limit: {sprite_size} bytes",
        )
    try:
        with Image.open(sprite_path) as opened:
            opened.load()
            image_format = opened.format
            image = opened.convert("RGBA") if opened.mode != "RGBA" else opened.copy()
            original_mode = opened.mode
    except (OSError, UnidentifiedImageError) as exc:
        report.add("error", "atlas.unreadable", str(exc), sprite_relative.as_posix())
        return report
    report.metadata.update(
        {
            "atlas_format": image_format,
            "atlas_mode": original_mode,
            "atlas_width": image.width,
            "atlas_height": image.height,
        }
    )
    if image_format not in {"WEBP", "PNG"}:
        report.add("error", "atlas.format", "atlas must decode as PNG or WebP")
    if original_mode != "RGBA":
        report.add("error", "atlas.mode", f"atlas must be RGBA, got {original_mode}")
    if image.size != (ATLAS_WIDTH, ATLAS_HEIGHT):
        report.add(
            "error",
            "atlas.dimensions",
            f"expected {ATLAS_WIDTH}x{ATLAS_HEIGHT}, got {image.width}x{image.height}",
        )
        return report
    _validate_cells(image, report)
    _validate_hidden_rgb(image, report)
    if verify_checksums:
        _validate_checksum_file(pet_dir, report)
    return report
