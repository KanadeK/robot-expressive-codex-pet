"""Codex v2 sprite contract used by the package and its validator."""

from __future__ import annotations

from dataclasses import dataclass

VERSION = "0.1.0"
PET_ID = "robot-expressive"
SPRITE_VERSION = 2
CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_COLUMNS = 8
ATLAS_ROWS = 11
ATLAS_WIDTH = CELL_WIDTH * ATLAS_COLUMNS
ATLAS_HEIGHT = CELL_HEIGHT * ATLAS_ROWS
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class RowSpec:
    """One row in the Codex v2 sprite atlas."""

    name: str
    row: int
    frames: int
    durations_ms: tuple[int, ...]

    def duration_for(self, frame: int) -> int:
        """Return the duration for a frame, extending the final value if needed."""

        return self.durations_ms[min(frame, len(self.durations_ms) - 1)]


STANDARD_ROWS: tuple[RowSpec, ...] = (
    RowSpec("idle", 0, 6, (280, 110, 110, 140, 140, 320)),
    RowSpec("running-right", 1, 8, (120, 120, 120, 120, 120, 120, 120, 220)),
    RowSpec("running-left", 2, 8, (120, 120, 120, 120, 120, 120, 120, 220)),
    RowSpec("waving", 3, 4, (140, 140, 140, 280)),
    RowSpec("jumping", 4, 5, (140, 140, 140, 140, 280)),
    RowSpec("failed", 5, 8, (140, 140, 140, 140, 140, 140, 140, 240)),
    RowSpec("waiting", 6, 6, (150, 150, 150, 150, 150, 260)),
    RowSpec("running", 7, 6, (120, 120, 120, 120, 120, 220)),
    RowSpec("review", 8, 6, (150, 150, 150, 150, 150, 280)),
)
LOOK_DIRECTIONS: tuple[str, ...] = (
    "000",
    "022.5",
    "045",
    "067.5",
    "090",
    "112.5",
    "135",
    "157.5",
    "180",
    "202.5",
    "225",
    "247.5",
    "270",
    "292.5",
    "315",
    "337.5",
)

ALL_ROWS: tuple[RowSpec, ...] = STANDARD_ROWS + (
    RowSpec("look-row-9", 9, 8, (150,) * 8),
    RowSpec("look-row-10", 10, 8, (150,) * 8),
)

REQUIRED_MANIFEST_FIELDS = (
    "id",
    "displayName",
    "description",
    "spriteVersionNumber",
    "spritesheetPath",
)
