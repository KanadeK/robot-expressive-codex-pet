# Deterministic rendering recipe

No image-generation prompt was used for the shipped spritesheet. Every frame is
rendered from the pinned `RobotExpressive.glb` file with its original skeletal
animations.

## Pinned inputs

- three.js: `0.185.1`
- Playwright: `1.62.0`
- upstream commit: `eba30de865cfbf31ac736f792defd9a60ff28d57`
- model SHA-256:
  `047f5e5fb3bb6d378bd1df16ca6137f2a596c99b3a1b5690b4020c05aaf6f319`
- viewport: orthographic, transparent, neutral three-light setup
- render scale: 4x, downsampled into `192x208` cells

## Animation mapping

| Codex row | Frames | Upstream clip | Camera / bone treatment |
| --- | ---: | --- | --- |
| Idle | 6 | `Idle` | front |
| Running right | 8 | `Running` | body yaw -90 degrees |
| Running left | 8 | `Running` | body yaw +90 degrees |
| Waving | 4 | `Wave` | front |
| Jumping | 5 | `Jump` | front |
| Failed | 8 | `Death` | front |
| Waiting | 6 | `Sitting` | front |
| Running / working | 6 | `Punch` | front |
| Review | 6 | `ThumbsUp` | front |
| Look directions | 16 | `Standing` | deterministic head yaw and pitch |

The renderer validates that every named clip and the head bone exist before it
draws anything. It uses one scale envelope across all sampled poses, aligns
every frame to a fixed baseline, clears unused cells to transparent black, and
writes a machine-readable report.

## Reproduce

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm run render
python scripts/finalize_atlas.py \
  --input tmp/robot-atlas.png \
  --render-report tmp/robot-render-report.json
python -m robot_pet validate pet --json
```

WebGL rasterization can vary by GPU and browser build, so byte identity is
guaranteed for packages built from the committed atlas, not across unrelated
graphics drivers. Geometry, animation mapping, populated cells, dimensions,
alpha safety, source hash, and package output are verified deterministically.
