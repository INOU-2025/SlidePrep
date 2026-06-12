#!/usr/bin/env python3
"""
Generate synthetic sample tiles for SlidePrep.

Creates 9 tiles (3×3 mosaic) cut from a single large canvas that replicates
the physical geometry of a Sedgwick-Rafter chamber imaged at the production
magnification:

  - Tile dimensions : 2048×1536 px  (665×499 µm at 0.324957 µm/px)
  - Overlap         : 10 %
  - Grid spacing    : 1000 µm ≈ 3077 px  — Sedgwick-Rafter line pitch
  - At most one horizontal and one vertical line per tile
  - Line angles     : 1.7° (horizontal family) and −88.3° (vertical family)
  - Line width      : 21 px

Tiles are sliced from a common canvas so overlap strips are pixel-consistent
and Ashlar can register them correctly.

Usage:
    python sample_data/generate_tiles.py
"""

from pathlib import Path

import cv2
import numpy as np
import tifffile

# ---------------------------------------------------------------------------
# Physical constants — must match production acquisition and config.json
# ---------------------------------------------------------------------------
TILE_W           = 2048          # px
TILE_H           = 1536          # px
PIXEL_SIZE_UM    = 0.324957      # µm/px
GRID_SPACING_UM  = 1000.0        # µm — Sedgwick-Rafter chamber line pitch
OVERLAP          = 0.10
COLS = ROWS      = 3

# ---------------------------------------------------------------------------
# Grid line appearance — match pipeline detector / refinement configuration
# ---------------------------------------------------------------------------
LINE_WIDTH       = 21            # px — matches thickness target in config
H_ANGLE_DEG      = 1.7           # degrees from x-axis (horizontal family)
V_ANGLE_DEG      = -88.3         # degrees from x-axis (vertical family)
LINE_INTENSITY   = 45            # darker than background, not pure black

# ---------------------------------------------------------------------------
# Background texture
# ---------------------------------------------------------------------------
BACKGROUND_LOW   = 80
BACKGROUND_HIGH  = 200
BG_NOISE_SIGMA   = 12
TOP_NOISE_SIGMA  = 8
SEED             = 42
# ---------------------------------------------------------------------------


def _draw_line(canvas: np.ndarray, cx: int, cy: int,
               angle_deg: float, thickness: int, intensity: int) -> None:
    """Draw a single line through (cx, cy) at angle_deg across the full canvas."""
    H, W = canvas.shape[:2]
    rad = np.deg2rad(angle_deg)
    L = int(np.hypot(W, H)) + 1
    dx = int(round(L * np.cos(rad)))
    dy = int(round(L * np.sin(rad)))
    cv2.line(canvas,
             (cx - dx, cy - dy),
             (cx + dx, cy + dy),
             intensity, thickness)


def generate(out_dir: Path) -> None:
    rng = np.random.default_rng(SEED)

    GRID_SPACING_PX = round(GRID_SPACING_UM / PIXEL_SIZE_UM)  # ≈ 3077
    STEP_X = int(TILE_W * (1 - OVERLAP))                      # 1843
    STEP_Y = int(TILE_H * (1 - OVERLAP))                      # 1382
    CANVAS_W = TILE_W + (COLS - 1) * STEP_X                  # 5734
    CANVAS_H = TILE_H + (ROWS - 1) * STEP_Y                  # 4300

    # --- background: diagonal gradient + Gaussian noise ---
    xx, yy = np.meshgrid(np.linspace(0.0, 1.0, CANVAS_W),
                         np.linspace(0.0, 1.0, CANVAS_H))
    gradient = BACKGROUND_LOW + (BACKGROUND_HIGH - BACKGROUND_LOW) * (xx + yy) / 2.0
    bg_noise = rng.normal(0.0, BG_NOISE_SIGMA, (CANVAS_H, CANVAS_W))
    canvas = np.clip(gradient + bg_noise, 0, 255).astype(np.uint8)

    # --- paint grid lines ---
    # Offset start to CANVAS//4 so lines land inside tiles rather than at
    # canvas edges, while preserving the physical 1000 µm inter-line spacing.
    h_anchors = list(range(CANVAS_H // 4, CANVAS_H + GRID_SPACING_PX, GRID_SPACING_PX))
    v_anchors = list(range(CANVAS_W // 4, CANVAS_W + GRID_SPACING_PX, GRID_SPACING_PX))

    for y in h_anchors:
        _draw_line(canvas, CANVAS_W // 2, y, H_ANGLE_DEG, LINE_WIDTH, LINE_INTENSITY)
    for x in v_anchors:
        _draw_line(canvas, x, CANVAS_H // 2, V_ANGLE_DEG, LINE_WIDTH, LINE_INTENSITY)

    # --- add light surface noise on top of lines ---
    top_noise = rng.normal(0.0, TOP_NOISE_SIGMA, (CANVAS_H, CANVAS_W))
    canvas = np.clip(canvas.astype(np.float32) + top_noise, 0, 255).astype(np.uint8)

    # --- slice into overlapping tiles and write with pixel-size metadata ---
    out_dir.mkdir(parents=True, exist_ok=True)

    series = 0
    for col in range(COLS):
        for row in range(ROWS):
            x0, y0 = col * STEP_X, row * STEP_Y
            tile = canvas[y0:y0 + TILE_H, x0:x0 + TILE_W]
            fname = out_dir / f"TileScan_001_s{series:03d}_ch00.tif"

            # ImageJ-compatible resolution: pixels per µm, unit tag = 'um'
            tifffile.imwrite(
                str(fname), tile,
                compression='lzw',
                imagej=True,
                resolution=(1.0 / PIXEL_SIZE_UM, 1.0 / PIXEL_SIZE_UM),
                metadata={'unit': 'um'},
            )

            n_h = sum(1 for y in h_anchors if y0 <= y < y0 + TILE_H)
            n_v = sum(1 for x in v_anchors if x0 <= x < x0 + TILE_W)
            print(f"  {fname.name}  col={col} row={row}  "
                  f"H-lines={n_h}  V-lines={n_v}")
            series += 1

    print(f"\n{COLS * ROWS} tiles written to {out_dir}/")
    print(f"Tile size       : {TILE_W}×{TILE_H} px  "
          f"({TILE_W * PIXEL_SIZE_UM:.0f}×{TILE_H * PIXEL_SIZE_UM:.0f} µm)")
    print(f"Grid spacing    : {GRID_SPACING_UM:.0f} µm = {GRID_SPACING_PX} px")
    print(f"H-line anchors  : y = {h_anchors}")
    print(f"V-line anchors  : x = {v_anchors}")


if __name__ == "__main__":
    generate(Path(__file__).parent / "tiles")
