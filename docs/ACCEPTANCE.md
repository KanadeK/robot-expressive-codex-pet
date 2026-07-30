# Acceptance and repair playbook

Run commands from the repository root. The shipped pet and Python tooling need
Python 3.11+. Re-rendering also needs Node.js 22+ and pnpm.

## 1. Environment and pinned inputs

```bash
python --version
node --version
pnpm --version
python -m pip install -e ".[dev]"
pnpm install --frozen-lockfile
pnpm run render:check
```

Expected: all commands exit `0`; Python is 3.11+, Node is 22+, and the renderer
check confirms required files, clips, and pinned dependency versions.

Verify the original character bytes:

```bash
python -c "import hashlib,pathlib; p=pathlib.Path('artwork/source/RobotExpressive.glb'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

Expected:

```text
047f5e5fb3bb6d378bd1df16ca6137f2a596c99b3a1b5690b4020c05aaf6f319
```

Repair:

- missing Python/Node: install a supported version and reopen the terminal;
- frozen-lockfile failure: do not delete the lock; use the declared pnpm
  version, resolve the dependency change intentionally, then commit both
  `package.json` and `pnpm-lock.yaml`;
- model hash mismatch: stop. Compare the file with the pinned three.js commit;
  never update the expected hash merely to make the gate green.

## 2. Optional full renderer regeneration

```bash
pnpm run render
python scripts/finalize_atlas.py \
  --input tmp/robot-atlas.png \
  --render-report tmp/robot-render-report.json
python -m robot_pet validate pet --json
```

Expected: renderer reports `"ok": true` and 73 populated cells; finalizer
reports `1536x2288`, RGBA, `"validationOk": true`.

Repair:

| Failure | Repair |
| --- | --- |
| no browser executable | install Chrome/Edge, or run `pnpm exec playwright install chromium` |
| module 404 | rerun `pnpm install --frozen-lockfile`; confirm Three.js `build/three.module.js` and `three.core.js` exist |
| missing clip/head | restore the pinned GLB; do not substitute a similarly named model |
| browser timeout | inspect logged browser/page errors; run with `--browser` pointing to a supported Chromium executable |
| cell clipping | adjust the global camera/scale envelope, regenerate the complete atlas, and inspect every state |
| output hash mismatch | delete only the generated `tmp/robot-atlas.png` and report, then rerun both renderer and finalizer |

Do not “fix” a failed frame by cloning an unrelated pose, populating unused
cells, painting over the source, or disabling a validator rule.

## 3. Static checks and tests

```bash
ruff check .
mypy src scripts
python -m compileall -q src scripts tests
coverage erase
coverage run -m unittest discover -s tests -v
coverage report
```

Expected: no lint/type errors, all tests `ok`, and at least 85% branch coverage.
Tests cover invalid atlases, checksum corruption, unsafe ZIP members,
transactional replacement and rollback, recoverable uninstall, deterministic
archives, renderer provenance, builds, previews, and CLI errors.

Repair one failure first:

```bash
python -m unittest tests.test_module.ClassName.test_name -v
```

Fix the smallest responsible component, rerun its module, then rerun the full
suite and coverage. Do not use a broad type ignore or reduce the threshold.

## 4. Build release and Pages inputs

```bash
robot-pet validate pet --json
python scripts/build_release.py --json
python scripts/build_site.py --json
pnpm run test:site
```

Expected:

- pet validation: `"ok": true`, zero errors, v2, RGBA, `1536x2288`;
- `dist/`: `.codex-pet.zip`, `pet.json`, `spritesheet.webp`, `SHA256SUMS`,
  `release-manifest.json`;
- `media/`: contact sheet, showcase GIF, and every semantic animation GIF;
- `site/`: interactive lab, validation JSON, metadata, and exact release atlas.
- E2E: real atlas loads, controls work, validation is PASS, and desktop/mobile
  layouts produce no browser error or horizontal overflow.

Common validator repairs:

| Code | Meaning | Repair |
| --- | --- | --- |
| `manifest.*` | missing, wrong, or unsafe manifest data | restore the documented v2 fields and a single local sprite filename |
| `atlas.dimensions` | atlas is not exactly `1536x2288` | rerun renderer/finalizer; never stretch the final image |
| `atlas.used_cell_empty` | required frame is transparent | diagnose its clip/job and regenerate the entire row |
| `atlas.unused_cell_populated` | data exists after a row's final frame | fix job allocation and regenerate; unused cells must be transparent black |
| `atlas.cell_touches_edge` | clipping risk | adjust global registration and inspect all poses |
| `atlas.hidden_rgb` | transparent pixels retain color | rerun finalization with transparent-black clearing |
| `checksums.mismatch` | tracked pet bytes changed | inspect the change, then deliberately rerun finalization/build |

## 5. Isolated install, doctor, and uninstall

These paths stay inside `tmp/` and do not touch the real Codex installation:

```bash
python scripts/install.py --source pet --pets-root tmp/acceptance-pets --backup-root tmp/acceptance-backups --json
python -m robot_pet doctor --pets-root tmp/acceptance-pets --json
python -m robot_pet uninstall --pets-root tmp/acceptance-pets --backup-root tmp/acceptance-backups --json
```

Expected: install and doctor return `"ok": true`; uninstall returns a backup
directory containing the manifest and atlas.

PowerShell wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1 `
  -Python python `
  -Source pet `
  -PetsRoot tmp\acceptance-pets `
  -BackupRoot tmp\acceptance-backups `
  -Json
```

Repair:

- permission denied: choose writable, explicit pets and backup roots;
- interrupted staging: verify the staging path is inside that test root, move
  it aside, and retry;
- invalid download: compare it with the Release `SHA256SUMS`, redownload, and
  never install on mismatch.

## 6. Determinism

```bash
python scripts/build_release.py --out-dir tmp/release-a --json
python scripts/build_release.py --out-dir tmp/release-b --json
python -c "import hashlib,pathlib; a=next(pathlib.Path('tmp/release-a').glob('*.zip')); b=next(pathlib.Path('tmp/release-b').glob('*.zip')); assert a.read_bytes()==b.read_bytes(); print(hashlib.sha256(a.read_bytes()).hexdigest())"
```

Expected: the assertion passes. If it fails, compare ZIP member order,
timestamps, modes, comments, compression, and source bytes. Remove wall-clock
metadata; do not normalize the result after packaging.

## 7. Strict release gate

After committing all intended files:

```bash
python scripts/release_check.py --json --strict
git status --short
git shortlog -sne HEAD
```

Expected: top-level `"ok": true`, empty Git status, and only the intended human
author. Also verify there are no co-author trailers:

```powershell
if (git log --format=%B | Select-String -Pattern 'Co-authored-by' -CaseSensitive:$false) {
  throw 'Unexpected Co-authored-by trailer'
}
```

If the app cannot resolve `git`, set the project-specific `ROBOT_PET_GIT`
environment variable to a trusted Git executable for that command.

Gate repair:

- `git_clean`: inspect status and commit intended files; never reset unrelated
  work;
- `model_provenance` or `render_provenance`: compare the report, source, and
  final atlas; regenerate from the pinned input rather than editing evidence;
- `deterministic_package`: inspect internal archive metadata and content;
- `secret_scan`: revoke any real exposed credential first, remove it from the
  tree and history, then rerun;
- wrong author: correct Git identity before publication and repair only the
  unpublished commit intentionally.
