## What changed

Describe the user-visible behavior and the failure mode addressed.

## Verification

- [ ] `ruff check .`
- [ ] `mypy src scripts`
- [ ] `pnpm install --frozen-lockfile`
- [ ] `pnpm run render:check`
- [ ] `coverage run -m unittest discover -s tests -v`
- [ ] `coverage report`
- [ ] `python scripts/build_release.py --json`
- [ ] `python scripts/release_check.py --json`

## Visual and license checks

- [ ] No visual asset was added without source, creator, and license provenance.
- [ ] Atlas changes preserve RobotExpressive's identity and pass row, direction, and motion QA.
- [ ] Code remains MIT and the source/rendered visual assets remain CC0 1.0.
