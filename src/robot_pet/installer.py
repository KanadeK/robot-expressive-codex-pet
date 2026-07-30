"""Transactional, checksum-aware install and recoverable uninstall operations."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .atlas import validate_pet_directory


@dataclass(frozen=True, slots=True)
class InstallResult:
    ok: bool
    action: str
    pet_id: str
    destination: str
    backup: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _next_backup_path(backup_root: Path, pet_id: str, action: str) -> Path:
    base = backup_root / f"{pet_id}-{action}-{_timestamp()}"
    candidate = base
    counter = 1
    while candidate.exists():
        candidate = backup_root / f"{base.name}-{counter}"
        counter += 1
    return candidate


def _assert_safe_zip_member(root: Path, member_name: str) -> Path:
    normalized = member_name.replace("\\", "/")
    relative = Path(normalized)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe archive member: {member_name}")
    destination = (root / relative).resolve()
    if root.resolve() not in destination.parents and destination != root.resolve():
        raise ValueError(f"archive member escapes extraction root: {member_name}")
    return destination


def safe_extract_zip(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = _assert_safe_zip_member(destination, member.filename)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def _locate_pet_dir(source: Path) -> Path:
    if (source / "pet.json").is_file():
        return source
    if (source / "pet" / "pet.json").is_file():
        return source / "pet"
    raise FileNotFoundError(f"no pet.json found in {source}")


def _pet_id(pet_dir: Path) -> str:
    manifest = json.loads((pet_dir / "pet.json").read_text(encoding="utf-8"))
    pet_id = manifest.get("id")
    if not isinstance(pet_id, str):
        raise ValueError("pet manifest has no string id")
    return pet_id


def install_pet(
    source: Path | str,
    *,
    pets_root: Path | str | None = None,
    backup_root: Path | str | None = None,
) -> InstallResult:
    source_path = Path(source).expanduser().resolve()
    resolved_pets_root = Path(pets_root or Path.home() / ".codex" / "pets").expanduser()
    resolved_backup_root = Path(
        backup_root or Path.home() / ".codex" / "pet-backups"
    ).expanduser()
    with tempfile.TemporaryDirectory(prefix="robot-expressive-install-") as temporary:
        temporary_root = Path(temporary)
        if source_path.is_file() and source_path.suffix.lower() == ".zip":
            safe_extract_zip(source_path, temporary_root)
            pet_dir = _locate_pet_dir(temporary_root)
        elif source_path.is_dir():
            pet_dir = _locate_pet_dir(source_path)
        else:
            raise FileNotFoundError(f"unsupported install source: {source_path}")
        report = validate_pet_directory(pet_dir)
        if not report.ok:
            raise ValueError(report.format_text())
        pet_id = _pet_id(pet_dir)
        destination = resolved_pets_root / pet_id
        resolved_pets_root.mkdir(parents=True, exist_ok=True)
        resolved_backup_root.mkdir(parents=True, exist_ok=True)
        staging = resolved_pets_root / f".{pet_id}.staging-{uuid.uuid4().hex}"
        backup: Path | None = None
        try:
            shutil.copytree(pet_dir, staging)
            staged_report = validate_pet_directory(staging)
            if not staged_report.ok:
                raise ValueError(staged_report.format_text())
            if destination.exists():
                backup = _next_backup_path(resolved_backup_root, pet_id, "backup")
                shutil.move(str(destination), str(backup))
            os.replace(staging, destination)
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            if backup is not None and backup.exists() and not destination.exists():
                shutil.move(str(backup), str(destination))
            raise
    return InstallResult(
        ok=True,
        action="install",
        pet_id=pet_id,
        destination=str(destination),
        backup=str(backup) if backup else None,
    )


def uninstall_pet(
    pet_id: str,
    *,
    pets_root: Path | str | None = None,
    backup_root: Path | str | None = None,
) -> InstallResult:
    resolved_pets_root = Path(pets_root or Path.home() / ".codex" / "pets").expanduser()
    resolved_backup_root = Path(
        backup_root or Path.home() / ".codex" / "pet-backups"
    ).expanduser()
    destination = resolved_pets_root / pet_id
    if not destination.is_dir():
        raise FileNotFoundError(f"pet is not installed: {destination}")
    resolved_backup_root.mkdir(parents=True, exist_ok=True)
    backup = _next_backup_path(resolved_backup_root, pet_id, "removed")
    shutil.move(str(destination), str(backup))
    return InstallResult(
        ok=True,
        action="uninstall",
        pet_id=pet_id,
        destination=str(destination),
        backup=str(backup),
    )


def doctor(
    pet_id: str,
    *,
    pets_root: Path | str | None = None,
) -> dict[str, object]:
    resolved_pets_root = Path(pets_root or Path.home() / ".codex" / "pets").expanduser()
    destination = resolved_pets_root / pet_id
    if not destination.is_dir():
        return {
            "ok": False,
            "pet_id": pet_id,
            "installed": False,
            "destination": str(destination),
            "issues": [{"code": "install.missing", "message": "pet directory is absent"}],
        }
    report = validate_pet_directory(destination)
    result = report.as_dict()
    result.update({"pet_id": pet_id, "installed": True, "destination": str(destination)})
    return result
