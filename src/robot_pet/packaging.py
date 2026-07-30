"""Reproducible release packaging for the Codex pet."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Iterable
from pathlib import Path

from .atlas import validate_pet_directory
from .checksums import sha256_file

ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _manifest_sprite_name(pet_dir: Path) -> str:
    manifest = json.loads((pet_dir / "pet.json").read_text(encoding="utf-8"))
    value = manifest["spritesheetPath"]
    if not isinstance(value, str):
        raise ValueError("spritesheetPath must be a string")
    return value


def build_deterministic_package(
    pet_dir: Path | str,
    output: Path | str,
    *,
    extra_files: Iterable[tuple[Path, str]] = (),
) -> Path:
    """Build a byte-for-byte reproducible .zip with the pet files at archive root."""

    source = Path(pet_dir).resolve()
    destination = Path(output).resolve()
    report = validate_pet_directory(source)
    if not report.ok:
        raise ValueError(report.format_text())
    sprite_name = _manifest_sprite_name(source)
    required = [
        (source / "pet.json", "pet.json"),
        (source / sprite_name, sprite_name),
        (source / "checksums.txt", "checksums.txt"),
    ]
    entries = required + list(extra_files)
    missing = [str(path) for path, _ in entries if not path.is_file()]
    if missing:
        raise FileNotFoundError("package inputs are missing: " + ", ".join(missing))
    archive_names = [name for _, name in entries]
    if len(archive_names) != len(set(archive_names)):
        raise ValueError("duplicate archive paths are not allowed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_output = destination.with_suffix(destination.suffix + ".tmp")
    with zipfile.ZipFile(
        temp_output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for source_path, archive_name in sorted(entries, key=lambda item: item[1]):
            archive.writestr(_zip_info(archive_name), source_path.read_bytes())
    temp_output.replace(destination)
    return destination


def package_sha256(path: Path | str) -> str:
    return sha256_file(Path(path))
