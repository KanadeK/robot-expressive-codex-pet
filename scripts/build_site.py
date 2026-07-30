"""Build the static interactive preview site from verified release inputs."""

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
from robot_pet.constants import VERSION


def _portable_validation(report_data: dict[str, object]) -> dict[str, object]:
    portable = dict(report_data)
    portable["target"] = "pet"
    metadata = cast(dict[str, object], portable["metadata"])
    portable["metadata"] = dict(metadata)
    spritesheet = cast(dict[str, object], portable["metadata"]).get("spritesheet")
    if isinstance(spritesheet, str):
        cast(dict[str, object], portable["metadata"])["spritesheet"] = (
            f"pet/{Path(spritesheet).name}"
        )
    return portable


def build_site(project_root: Path, output_dir: Path) -> dict[str, object]:
    report = validate_pet_directory(project_root / "pet")
    if not report.ok:
        raise ValueError(report.format_text())
    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "assets").mkdir(parents=True)
    for filename in ("index.html", "site.css", "site.js"):
        shutil.copy2(project_root / "web" / filename, output_dir / filename)
    shutil.copy2(project_root / "pet" / "spritesheet.webp", output_dir / "assets/spritesheet.webp")
    showcase = project_root / "media" / "showcase.gif"
    if showcase.is_file():
        shutil.copy2(showcase, output_dir / "assets/showcase.gif")
    validation_path = output_dir / "assets" / "validation.json"
    portable_validation = _portable_validation(report.as_dict())
    validation_path.write_text(
        json.dumps(portable_validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    metadata = {
        "version": VERSION,
        "pet_id": report.metadata["pet_id"],
        "sprite_version_number": report.metadata["sprite_version_number"],
        "spritesheet_sha256": report.metadata["spritesheet_sha256"],
    }
    (output_dir / "assets" / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"ok": True, "site": str(output_dir), "validation": portable_validation}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "site")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_site(args.project_root.resolve(), args.out_dir.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}))
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Built site at {result['site']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
