"""Install the repository pet with validation, backup, and rollback."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from robot_pet.installer import doctor, install_pet


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and transactionally install RobotExpressive "
            "into a Codex pets directory."
        )
    )
    parser.add_argument("--source", type=Path, default=PROJECT_ROOT / "pet")
    parser.add_argument("--pets-root", type=Path)
    parser.add_argument("--backup-root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = install_pet(
            args.source,
            pets_root=args.pets_root,
            backup_root=args.backup_root,
        )
        diagnosis = doctor(result.pet_id, pets_root=args.pets_root)
        payload = {"ok": bool(diagnosis["ok"]), "install": result.as_dict(), "doctor": diagnosis}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif payload["ok"]:
        install_data = payload["install"]
        assert isinstance(install_data, dict)
        print(f"Installed RobotExpressive at {install_data['destination']}")
        if install_data["backup"]:
            print(f"Previous installation backed up at {install_data['backup']}")
        print("Doctor: PASS")
    else:
        print(f"Install failed: {payload['message']}", file=sys.stderr)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
