# Release runbook

The release is complete only when the public repository, CI, Pages deployment,
tagged GitHub Release, downloadable assets, hashes, and contributor identity
are all verified.

## 1. Local preflight

```bash
pnpm install --frozen-lockfile
pnpm run render:check
python -m pip install -e ".[dev]"
ruff check .
mypy src scripts
coverage run -m unittest discover -s tests -v
coverage report
python scripts/build_release.py --json
python scripts/build_site.py --json
pnpm run test:site
```

Visually inspect:

- `media/contact-sheet.png`;
- every file under `media/actions/`;
- `media/showcase.gif`;
- the responsive and reduced-motion behavior of the built site.

## 2. Commit hygiene

Configure the intended human identity before committing:

```bash
git config user.name "KanadeK"
git config user.email "121669563+KanadeK@users.noreply.github.com"
git add .
git commit -m "Release RobotExpressive Codex Pet v0.1.0"
python scripts/release_check.py --json --strict
git shortlog -sne HEAD
git log --format="%H%n%an <%ae>%n%cn <%ce>%n%B"
```

Confirm a clean tree, the correct author and committer, and no
`Co-authored-by` trailer.

## 3. Create and push the public repository

```bash
gh auth status
gh repo create KanadeK/robot-expressive-codex-pet \
  --public \
  --source . \
  --remote origin \
  --description "Reproducible CC0 RobotExpressive Codex v2 pet with offline renderer, validator, and safe installer." \
  --push
```

Set topics:

```bash
gh repo edit KanadeK/robot-expressive-codex-pet \
  --add-topic codex \
  --add-topic codex-pet \
  --add-topic threejs \
  --add-topic robot-expressive \
  --add-topic webgl \
  --add-topic desktop-pet \
  --add-topic reproducible-builds
```

Enable GitHub Pages with GitHub Actions as its source if the repository does
not already expose that setting.

## 4. Verify branch workflows

Wait for both workflows on the pushed commit:

```bash
gh run list --repo KanadeK/robot-expressive-codex-pet --limit 20
gh run watch RUN_ID --repo KanadeK/robot-expressive-codex-pet --exit-status
```

Open the Pages URL and verify it loads the real atlas and reports `PASS`.
Fix failures on `main`, rerun all local gates, commit, and push before tagging.

## 5. Tag and publish

```bash
git tag -a v0.1.0 -m "RobotExpressive Codex Pet v0.1.0"
git push origin v0.1.0
```

The tag workflow builds and publishes:

- `robot-expressive-v0.1.0.codex-pet.zip`
- `pet.json`
- `spritesheet.webp`
- `SHA256SUMS`
- `release-manifest.json`

Wait until the workflow and Release are terminal and successful.

## 6. Download and independently verify

Use a new empty directory:

```bash
gh release download v0.1.0 \
  --repo KanadeK/robot-expressive-codex-pet \
  --dir tmp/downloaded-release
```

Compare every listed SHA-256, inspect ZIP member paths and fixed timestamps,
extract into a new directory, and run:

```bash
robot-pet validate tmp/downloaded-pet --json
```

Also verify:

- the public default branch points to the tested commit;
- Release tag and target commit match;
- all expected assets exist and are non-empty;
- CI, Pages, and Release checks are green;
- GitHub contributors show only intended human contributors;
- repository description, topics, license detection, README images, and links
  render correctly while logged out.

## 7. Notification

Only after all online checks pass, send the owner a Gmail message containing:

- public repository URL;
- live Pages URL;
- Release URL and tag;
- source commit;
- pet ZIP SHA-256;
- CI/Pages/Release status;
- short install and acceptance commands.

If Gmail sending fails, keep the verified public release intact, report the
mail failure accurately, and retry only the notification.
