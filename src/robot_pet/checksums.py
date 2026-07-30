"""SHA-256 helpers shared by package, installer, and release tooling."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checksum_lines(root: Path, relative_paths: Iterable[Path]) -> list[str]:
    paths = sorted(relative_paths, key=lambda item: item.as_posix())
    return [f"{sha256_file(root / path)}  {path.as_posix()}" for path in paths]


def write_checksums(root: Path, relative_paths: Iterable[Path], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(checksum_lines(root, relative_paths)) + "\n"
    output.write_text(content, encoding="utf-8", newline="\n")


def parse_checksums(path: Path) -> list[tuple[str, Path]]:
    entries: list[tuple[str, Path]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError(f"invalid checksum line {line_number}: {raw_line!r}")
        relative = Path(parts[1].lstrip("* "))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe checksum path on line {line_number}: {relative}")
        entries.append((parts[0].lower(), relative))
    return entries
