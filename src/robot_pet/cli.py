"""Command-line interface for validation, packaging, previews, and installation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .atlas import validate_pet_directory
from .constants import PET_ID, VERSION
from .installer import doctor, install_pet, uninstall_pet
from .packaging import build_deterministic_package, package_sha256
from .preview import render_previews


def _emit(payload: dict[str, Any], *, as_json: bool, text: str | None = None) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif text is not None:
        print(text)
    else:
        print(payload)


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="robot-pet",
        description=(
            "Validate, preview, package, install, and diagnose "
            "the RobotExpressive Codex pet."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a v2 pet directory")
    validate.add_argument("path", nargs="?", default="pet")
    validate.add_argument("--skip-checksums", action="store_true")
    _add_json_flag(validate)

    preview = subparsers.add_parser("preview", help="render deterministic GIF and sheet previews")
    preview.add_argument("path", nargs="?", default="pet")
    preview.add_argument("--output", default="media/actions")
    _add_json_flag(preview)

    package = subparsers.add_parser("pack", help="build a deterministic .codex-pet.zip")
    package.add_argument("path", nargs="?", default="pet")
    package.add_argument("--output", default=f"dist/{PET_ID}-v{VERSION}.codex-pet.zip")
    package.add_argument("--project-root", default=".")
    _add_json_flag(package)

    install = subparsers.add_parser("install", help="transactionally install a directory or ZIP")
    install.add_argument("source", nargs="?", default="pet")
    install.add_argument("--pets-root")
    install.add_argument("--backup-root")
    _add_json_flag(install)

    remove = subparsers.add_parser(
        "uninstall",
        help="move an installed pet into recoverable backup",
    )
    remove.add_argument("--pet-id", default=PET_ID)
    remove.add_argument("--pets-root")
    remove.add_argument("--backup-root")
    _add_json_flag(remove)

    diagnose = subparsers.add_parser("doctor", help="validate the installed pet")
    diagnose.add_argument("--pet-id", default=PET_ID)
    diagnose.add_argument("--pets-root")
    _add_json_flag(diagnose)
    return parser


def _package_extras(project_root: Path) -> list[tuple[Path, str]]:
    candidates = (
        ("NOTICE.md", "NOTICE.md"),
        ("ASSET_LICENSE.md", "ASSET_LICENSE.md"),
        ("LICENSE", "LICENSE-CODE-MIT.txt"),
    )
    return [
        (project_root / source, archive_name)
        for source, archive_name in candidates
        if (project_root / source).is_file()
    ]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            report = validate_pet_directory(args.path, verify_checksums=not args.skip_checksums)
            _emit(report.as_dict(), as_json=args.json, text=report.format_text())
            return 0 if report.ok else 1
        if args.command == "preview":
            preview_result = render_previews(args.path, args.output)
            _emit(
                preview_result,
                as_json=args.json,
                text=f"Rendered previews in {preview_result['output_dir']}",
            )
            return 0
        if args.command == "pack":
            project_root = Path(args.project_root).resolve()
            output = build_deterministic_package(
                args.path,
                args.output,
                extra_files=_package_extras(project_root),
            )
            payload = {
                "ok": True,
                "package": str(output),
                "sha256": package_sha256(output),
            }
            _emit(payload, as_json=args.json, text=f"{output}\nsha256={payload['sha256']}")
            return 0
        if args.command == "install":
            install_result = install_pet(
                args.source,
                pets_root=args.pets_root,
                backup_root=args.backup_root,
            )
            _emit(
                install_result.as_dict(),
                as_json=args.json,
                text=f"Installed {install_result.pet_id} to {install_result.destination}",
            )
            return 0
        if args.command == "uninstall":
            uninstall_result = uninstall_pet(
                args.pet_id,
                pets_root=args.pets_root,
                backup_root=args.backup_root,
            )
            _emit(
                uninstall_result.as_dict(),
                as_json=args.json,
                text=(
                    f"Moved {uninstall_result.pet_id} to recoverable backup "
                    f"{uninstall_result.backup}"
                ),
            )
            return 0
        if args.command == "doctor":
            doctor_result = doctor(args.pet_id, pets_root=args.pets_root)
            _emit(
                doctor_result,
                as_json=args.json,
                text=("PASS" if doctor_result["ok"] else "FAIL")
                + f": {doctor_result['destination']}",
            )
            return 0 if doctor_result["ok"] else 1
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        _emit(payload, as_json=getattr(args, "json", False), text=f"ERROR: {exc}")
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
