# Research, novelty, and project fit

Research snapshot: **2026-07-30**. Counts and search results are time-dependent.

## Constraints

The selected project had to:

1. use a real, existing character hosted on GitHub rather than an invented
   imitation;
2. have primary-source licensing suitable for a public derived pet;
3. avoid overlap with the owner's existing local projects and prior discussed
   pet concepts;
4. support real Codex v2 behavior rather than a UI-only showcase;
5. have a credible discoverability story without claiming that stars can be
   guaranteed.

The local project inventory included data/privacy tools, documentation
flight-checkers, game-feel tools, manual-maintenance planning, and an
unpublished Kiki pet draft. None used RobotExpressive or a GLB-to-Codex
animation pipeline.

## Candidates

| Candidate | Primary GitHub source | License confidence | Animation suitability | Decision |
| --- | --- | --- | --- | --- |
| RobotExpressive | official three.js example | CC0 stated in model README | 14 named skeletal clips; excellent | Selected |
| Kiki the Cyber Squirrel | KDE/Krita | GPL or CC BY-SA for official art | source art is static; rigged third-party downloads add account/license friction | Rejected for this release |
| Mixamo Xbot / Soldier examples | three.js examples | redistribution terms not as simple as the selected CC0 model | strong | Rejected on license clarity |
| Unnamed generated mascot | none | project-owned | arbitrary | Rejected because the character would be invented |

## Why RobotExpressive

RobotExpressive is a named, existing character in the official
[`mrdoob/three.js` repository][three-repo]. Its
[model README][model-readme] credits Tomás Laulhé for the model and Don McCurdy
for modifications, and states **CC0 1.0**.

The pinned GLB contains these animation clips:

```text
Dance, Death, Idle, Jump, No, Punch, Running, Sitting, Standing,
ThumbsUp, Walking, WalkJump, Wave, Yes
```

That animation vocabulary maps naturally to Codex states and avoids fake
motion made by duplicating frames. The source is only 463,988 bytes and can be
rendered locally with a reproducible, inspectable pipeline.

At the snapshot time, the GitHub API reported **114,109 stars** for three.js.
This does not transfer stars to a derivative project, but it demonstrates
existing developer recognition around the source ecosystem.

## GitHub novelty checks

The following repository/code searches were performed before implementation:

- `RobotExpressive Codex pet`
- `"RobotExpressive" "Codex pet"`
- `RobotExpressive spriteVersionNumber`
- `robot expressive desktop pet codex`

No existing repository or code result implementing RobotExpressive as a Codex
v2 pet was found at the snapshot time. Search absence is evidence of a
reasonable novelty check, not a permanent exclusivity claim.

## Why the repository can earn attention

The project is intentionally more useful than a novelty sprite:

- it bridges a well-known Three.js asset and a new Codex pet format;
- it offers an offline GLB-to-atlas renderer others can inspect and adapt;
- it validates semantic cells and hostile package inputs, not only image size;
- it provides a live lab driven by the exact release atlas;
- it has bilingual documentation, one-command acceptance, CI, Pages, and
  signed-by-hash release artifacts;
- searchable topics connect `threejs`, `robot-expressive`, `codex-pet`,
  `webgl`, `desktop-pet`, and `reproducible-builds`.

Stars and views depend on distribution, timing, and community interest, so the
project promises verifiable quality and discoverability—not a guaranteed
metric.

## Pinned evidence

- repository: `https://github.com/mrdoob/three.js`
- commit: `eba30de865cfbf31ac736f792defd9a60ff28d57`
- source path:
  `examples/models/gltf/RobotExpressive/RobotExpressive.glb`
- source SHA-256:
  `047f5e5fb3bb6d378bd1df16ca6137f2a596c99b3a1b5690b4020c05aaf6f319`
- license: CC0 1.0

[three-repo]: https://github.com/mrdoob/three.js
[model-readme]: https://github.com/mrdoob/three.js/blob/eba30de865cfbf31ac736f792defd9a60ff28d57/examples/models/gltf/RobotExpressive/README.md
