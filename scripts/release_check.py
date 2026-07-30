"""Release gate covering package validity, determinism, provenance, and Git hygiene."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from robot_pet.atlas import validate_pet_directory
from robot_pet.checksums import sha256_file
from robot_pet.packaging import build_deterministic_package

EXPECTED_MODEL_SHA256 = "047f5e5fb3bb6d378bd1df16ca6137f2a596c99b3a1b5690b4020c05aaf6f319"
EXPECTED_UPSTREAM_COMMIT = "eba30de865cfbf31ac736f792defd9a60ff28d57"
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
}
SKIP_DIRS = {
    ".git",
    ".hatch",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "site",
    "tmp",
    "__pycache__",
}


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str


class ReleaseResult(TypedDict):
    ok: bool
    strict: bool
    checks: list[dict[str, object]]
    pet_validation: dict[str, object]


def _run_git(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git_executable = os.environ.get("ROBOT_PET_GIT", "git")
    return subprocess.run(
        [git_executable, *args],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _project_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in project_root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _scan_secrets(project_root: Path) -> tuple[bool, str]:
    findings: list[str] = []
    for path in _project_files(project_root):
        if path.suffix.lower() in {".glb", ".png", ".webp", ".gif", ".zip", ".ico"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(project_root).as_posix()}:{name}")
    return not findings, "none" if not findings else ", ".join(findings)


def _required_files(project_root: Path) -> Check:
    required = (
        "README.md",
        "LICENSE",
        "ASSET_LICENSE.md",
        "NOTICE.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CITATION.cff",
        "package.json",
        "pnpm-lock.yaml",
        "pyproject.toml",
        "pet/pet.json",
        "pet/spritesheet.webp",
        "pet/checksums.txt",
        ".github/workflows/ci.yml",
        ".github/workflows/pages.yml",
        ".github/workflows/release.yml",
        "artwork/PROVENANCE.json",
        "artwork/RENDERING.md",
        "artwork/RENDER_REPORT.json",
        "artwork/source/RobotExpressive.glb",
        "scripts/finalize_atlas.py",
        "scripts/check_site.mjs",
        "scripts/install.py",
        "scripts/install.ps1",
        "scripts/install.sh",
        "scripts/render_atlas.mjs",
        "web/index.html",
        "web/site.css",
        "web/site.js",
        "docs/ACCEPTANCE.md",
        "docs/ARCHITECTURE.md",
        "docs/RESEARCH.md",
        "docs/RELEASE.md",
    )
    missing = [name for name in required if not (project_root / name).is_file()]
    detail = "none missing" if not missing else ", ".join(missing)
    return Check("required_files", not missing, detail)


def _model_provenance(project_root: Path) -> Check:
    model = project_root / "artwork" / "source" / "RobotExpressive.glb"
    if not model.is_file():
        return Check("model_provenance", False, "pinned RobotExpressive model is missing")
    actual = sha256_file(model)
    return Check(
        "model_provenance",
        actual == EXPECTED_MODEL_SHA256,
        f"sha256={actual}",
    )


def _render_provenance(project_root: Path) -> Check:
    report_path = project_root / "artwork" / "RENDER_REPORT.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        source = report["source"]
        atlas = report["atlas"]
        actual_atlas_hash = sha256_file(project_root / "pet" / "spritesheet.webp")
        ok = (
            source["modelSha256"] == EXPECTED_MODEL_SHA256
            and source["upstreamCommit"] == EXPECTED_UPSTREAM_COMMIT
            and source["license"] == "CC0-1.0"
            and atlas["sha256"] == actual_atlas_hash
            and atlas["populatedCells"] == 73
            and atlas["validationOk"] is True
        )
        detail = (
            f"commit={source['upstreamCommit']} "
            f"atlas_sha256={actual_atlas_hash} populated={atlas['populatedCells']}"
        )
        return Check("render_provenance", ok, detail)
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return Check("render_provenance", False, f"{type(exc).__name__}: {exc}")


def _deterministic_package(project_root: Path) -> Check:
    extras = [
        (project_root / "NOTICE.md", "NOTICE.md"),
        (project_root / "ASSET_LICENSE.md", "ASSET_LICENSE.md"),
        (project_root / "LICENSE", "LICENSE-CODE-MIT.txt"),
    ]
    with tempfile.TemporaryDirectory(prefix="robot-release-check-") as temporary:
        first = Path(temporary) / "first.zip"
        second = Path(temporary) / "second.zip"
        build_deterministic_package(project_root / "pet", first, extra_files=extras)
        time.sleep(1.1)
        build_deterministic_package(project_root / "pet", second, extra_files=extras)
        first_hash = sha256_file(first)
        second_hash = sha256_file(second)
    return Check(
        "deterministic_package",
        first_hash == second_hash,
        f"first={first_hash} second={second_hash}",
    )


def _git_checks(project_root: Path, strict: bool) -> list[Check]:
    checks: list[Check] = []
    status = _run_git(project_root, "status", "--porcelain")
    clean = status.returncode == 0 and not status.stdout.strip()
    checks.append(
        Check(
            "git_clean",
            clean if strict else status.returncode == 0,
            "clean" if clean else (status.stdout.strip() or status.stderr.strip()),
        )
    )
    count = _run_git(project_root, "rev-list", "--count", "HEAD")
    if count.returncode != 0:
        checks.append(Check("git_history", not strict, "no commit exists yet"))
        return checks
    log = _run_git(project_root, "log", "--format=%H%n%an <%ae>%n%cn <%ce>%n%B")
    has_coauthor = "co-authored-by:" in log.stdout.lower()
    coauthor_detail = "none" if not has_coauthor else "found"
    checks.append(Check("no_coauthored_by", not has_coauthor, coauthor_detail))
    shortlog = _run_git(project_root, "shortlog", "-sne", "HEAD")
    checks.append(
        Check(
            "git_authors",
            shortlog.returncode == 0 and bool(shortlog.stdout.strip()),
            shortlog.stdout.strip() or shortlog.stderr.strip(),
        )
    )
    return checks


def run_release_check(project_root: Path, strict: bool) -> ReleaseResult:
    checks = [
        _required_files(project_root),
        _model_provenance(project_root),
        _render_provenance(project_root),
    ]
    report = validate_pet_directory(project_root / "pet")
    checks.append(
        Check(
            "pet_validation",
            report.ok,
            f"errors={report.error_count} warnings={report.warning_count}",
        )
    )
    if report.ok:
        try:
            checks.append(_deterministic_package(project_root))
        except (OSError, ValueError) as exc:
            checks.append(Check("deterministic_package", False, str(exc)))
    secrets_ok, secrets_detail = _scan_secrets(project_root)
    checks.append(Check("secret_scan", secrets_ok, secrets_detail))
    checks.extend(_git_checks(project_root, strict))
    return {
        "ok": all(check.ok for check in checks),
        "strict": strict,
        "checks": [asdict(check) for check in checks],
        "pet_validation": report.as_dict(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_release_check(args.project_root.resolve(), args.strict)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for check in result["checks"]:
            marker = "PASS" if check["ok"] else "FAIL"
            print(f"{marker} {check['name']}: {check['detail']}")
        print("PASS release gate" if result["ok"] else "FAIL release gate")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
