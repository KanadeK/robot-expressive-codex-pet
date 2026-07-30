# Contributing

Thank you for improving RobotExpressive Codex Pet.

## Set up

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
corepack enable
pnpm install --frozen-lockfile
```

Run the local gate:

```bash
pnpm run render:check
ruff check .
mypy src scripts
coverage run -m unittest discover -s tests -v
coverage report
python scripts/build_release.py --json
python scripts/build_site.py --json
pnpm run test:site
python scripts/release_check.py --json
```

## Renderer and visual changes

Do not hand-edit isolated atlas cells. Change the renderer, rerun the complete
atlas, inspect every generated GIF and the contact sheet, and commit the
updated render report and checksums together.

A visual change must:

- keep the pinned source model and original identity unless the proposal
  explicitly updates provenance and license review;
- keep all 11 standard v2 rows, 73 required populated cells, and 16 look
  directions;
- use real source animation or a documented deterministic bone transform;
- preserve transparent unused cells and safe padding;
- pass the renderer smoke check, Python validator, tests, and release gate.

If changing the source model or upstream commit, explain why, verify the new
license from a primary source, and update every pinned hash. Never update a hash
merely to silence a failed provenance check.

## Pull requests

- Explain user-visible behavior and the failure mode being addressed.
- Add or update tests for code changes.
- Keep `dist/`, `site/`, `tmp/`, caches, dependencies, and virtual
  environments out of Git.
- Do not add `Co-authored-by` trailers for tools or people who did not author
  the change.
- Code contributions are MIT; rendered visual contributions are offered under
  CC0 1.0.
