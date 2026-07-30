"""Build previews, a deterministic pet archive, and release checksums."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from robot_pet.atlas import validate_pet_directory
from robot_pet.checksums import sha256_file, write_checksums
from robot_pet.constants import PET_ID, VERSION
from robot_pet.packaging import build_deterministic_package
from robot_pet.preview import render_previews


def _portable_validation(report_data: dict[str, object], sprite_name: str) -> dict[str, object]:
    portable = dict(report_data)
    portable["target"] = "pet"
    metadata = cast(dict[str, object], portable["metadata"])
    portable["metadata"] = dict(metadata)
    cast(dict[str, object], portable["metadata"])["spritesheet"] = f"pet/{sprite_name}"
    return portable


def build_release(project_root: Path, output_dir: Path) -> dict[str, object]:
    pet_dir = project_root / "pet"
    manifest = json.loads((pet_dir / "pet.json").read_text(encoding="utf-8"))
    sprite_name = manifest["spritesheetPath"]
    if not isinstance(sprite_name, str):
        raise ValueError("spritesheetPath must be a string")
    write_checksums(
        pet_dir,
        (Path("pet.json"), Path(sprite_name)),
        pet_dir / "checksums.txt",
    )
    report = validate_pet_directory(pet_dir)
    if not report.ok:
        raise ValueError(report.format_text())

    media_actions = project_root / "media" / "actions"
    preview_result = render_previews(pet_dir, media_actions)
    shutil.copy2(media_actions / "contact-sheet.png", project_root / "media" / "contact-sheet.png")
    shutil.copy2(media_actions / "idle.gif", project_root / "media" / "showcase.gif")

    output_dir.mkdir(parents=True, exist_ok=True)
    release_pet_manifest = output_dir / "pet.json"
    release_sprite = output_dir / Path(sprite_name).name
    shutil.copy2(pet_dir / "pet.json", release_pet_manifest)
    shutil.copy2(pet_dir / sprite_name, release_sprite)
    package_path = output_dir / f"{PET_ID}-v{VERSION}.codex-pet.zip"
    extras = [
        (project_root / "NOTICE.md", "NOTICE.md"),
        (project_root / "ASSET_LICENSE.md", "ASSET_LICENSE.md"),
        (project_root / "LICENSE", "LICENSE-CODE-MIT.txt"),
    ]
    build_deterministic_package(pet_dir, package_path, extra_files=extras)
    release_files = [
        package_path,
        release_pet_manifest,
        release_sprite,
    ]
    checksum_lines = [
        f"{sha256_file(path)}  {path.name}" for path in sorted(release_files, key=lambda p: p.name)
    ]
    checksum_path = output_dir / "SHA256SUMS"
    checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8", newline="\n")
    portable_validation = _portable_validation(report.as_dict(), sprite_name)
    release_manifest = {
        "schema_version": 1,
        "project": "robot-expressive-codex-pet",
        "version": VERSION,
        "pet_id": PET_ID,
        "sprite_version_number": 2,
        "artifacts": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in release_files
        },
        "validation": portable_validation,
    }
    manifest_path = output_dir / "release-manifest.json"
    manifest_path.write_text(
        json.dumps(release_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "ok": True,
        "package": str(package_path),
        "package_sha256": sha256_file(package_path),
        "checksums": str(checksum_path),
        "manifest": str(manifest_path),
        "previews": preview_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_release(args.project_root.resolve(), args.out_dir.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Built {result['package']}")
        print(f"sha256={result['package_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
