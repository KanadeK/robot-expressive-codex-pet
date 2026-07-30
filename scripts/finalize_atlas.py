#!/usr/bin/env python3
"""Convert the deterministic WebGL PNG into the packaged lossless WebP atlas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from robot_pet.atlas import validate_pet_directory  # noqa: E402
from robot_pet.checksums import sha256_file, write_checksums  # noqa: E402
from robot_pet.constants import (  # noqa: E402
    ALL_ROWS,
    ATLAS_HEIGHT,
    ATLAS_WIDTH,
    CELL_HEIGHT,
    CELL_WIDTH,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "tmp" / "robot-atlas.png",
        help="WebGL-rendered RGBA PNG",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "pet" / "spritesheet.webp",
        help="Lossless Codex v2 WebP atlas",
    )
    parser.add_argument(
        "--render-report",
        type=Path,
        default=PROJECT_ROOT / "tmp" / "robot-render-report.json",
        help="Report emitted by render_atlas.mjs",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "artwork" / "RENDER_REPORT.json",
        help="Portable final asset report",
    )
    return parser


def _cell_alpha_bbox(image: Image.Image, row: int, column: int) -> list[int] | None:
    cell = image.crop(
        (
            column * CELL_WIDTH,
            row * CELL_HEIGHT,
            (column + 1) * CELL_WIDTH,
            (row + 1) * CELL_HEIGHT,
        )
    )
    bbox = cell.getchannel("A").getbbox()
    return list(bbox) if bbox else None


def _analyze_cells(image: Image.Image) -> tuple[list[dict[str, Any]], list[str]]:
    cells: list[dict[str, Any]] = []
    failures: list[str] = []
    row_frames = {spec.row: spec.frames for spec in ALL_ROWS}

    for row in range(11):
        expected_frames = row_frames[row]
        for column in range(8):
            bbox = _cell_alpha_bbox(image, row, column)
            should_be_populated = column < expected_frames
            cells.append(
                {
                    "row": row,
                    "column": column,
                    "expected": "populated" if should_be_populated else "blank",
                    "alphaBbox": bbox,
                }
            )
            if should_be_populated and bbox is None:
                failures.append(f"required cell r{row}c{column} is blank")
            if not should_be_populated and bbox is not None:
                failures.append(f"unused cell r{row}c{column} contains pixels")
            if bbox is not None:
                left, top, right, bottom = bbox
                if left <= 1 or top <= 1 or right >= CELL_WIDTH - 1 or bottom >= CELL_HEIGHT - 1:
                    failures.append(f"cell r{row}c{column} touches its safety edge")
    return cells, failures


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    render_report_path = args.render_report.resolve()
    report_path = args.report.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"rendered atlas is missing: {input_path}")
    if not render_report_path.is_file():
        raise FileNotFoundError(f"render report is missing: {render_report_path}")

    render_report = json.loads(render_report_path.read_text(encoding="utf-8"))
    source_hash = sha256_file(input_path)
    if render_report["output"]["sha256"] != source_hash:
        raise ValueError("rendered atlas hash does not match the renderer report")

    with Image.open(input_path) as opened:
        image = opened.convert("RGBA")
    if image.size != (ATLAS_WIDTH, ATLAS_HEIGHT):
        raise ValueError(
            f"rendered atlas is {image.size}; expected {(ATLAS_WIDTH, ATLAS_HEIGHT)}"
        )
    cells, failures = _analyze_cells(image)
    if failures:
        raise ValueError("rendered atlas failed cell checks:\n- " + "\n- ".join(failures))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="WEBP", lossless=True, quality=100, method=6, exact=True)
    checksum_path = output_path.parent / "checksums.txt"
    write_checksums(
        output_path.parent,
        [Path("pet.json"), Path(output_path.name)],
        checksum_path,
    )

    validation = validate_pet_directory(output_path.parent)
    if not validation.ok:
        raise ValueError(f"final atlas validation failed:\n{validation.format_text()}")

    portable_report = {
        "schemaVersion": 1,
        "source": {
            "model": "artwork/source/RobotExpressive.glb",
            "modelSha256": render_report["model"]["sha256"],
            "upstreamRepository": "https://github.com/mrdoob/three.js",
            "upstreamCommit": "eba30de865cfbf31ac736f792defd9a60ff28d57",
            "upstreamPath": "examples/models/gltf/RobotExpressive/RobotExpressive.glb",
            "license": "CC0-1.0",
        },
        "renderer": {
            "threeRevision": render_report["threeRevision"],
            "browser": render_report["browser"],
            "webglRenderer": render_report["webgl"]["renderer"],
            "inputPngSha256": source_hash,
        },
        "atlas": {
            "path": "pet/spritesheet.webp",
            "sha256": sha256_file(output_path),
            "width": ATLAS_WIDTH,
            "height": ATLAS_HEIGHT,
            "mode": image.mode,
            "populatedCells": sum(1 for cell in cells if cell["alphaBbox"]),
            "validationOk": validation.ok,
        },
        "cells": cells,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(portable_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return portable_report


def main() -> int:
    args = build_parser().parse_args()
    report = finalize(args)
    print(json.dumps(report["atlas"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
