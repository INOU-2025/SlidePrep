#!/usr/bin/env python3
"""
Generate synthetic sample tiles for SlidePrep.

Creates 9 tiles (3×3 mosaic) with a simulated Sedgwick-Rafter chamber
background and two families of intersecting grid lines:
  - horizontal lines at H_ANGLE_DEG  (1.7°)
  - vertical   lines at V_ANGLE_DEG  (−88.3°)
Both match the target_inclination_angles in sample_data/config.json so the
full pipeline (binarization → detection → refinement → inpainting → stitching)
exercises every stage correctly.

Usage:
    python sample_data/generate_tiles.py
"""

from pathlib import Path

import cv2
import numpy as np
import tifffile

# ---------------------------------------------------------------------------
# Tuneable constants
# ---------------------------------------------------------------------------
TILE_SIZE       = 512
OVERLAP         = 0.10
COLS = ROWS     = 3
LINE_WIDTH      = 21          # px — matches the detector's thickness target
H_ANGLE_DEG     = 1.7         # horizontal grid line tilt (degrees from x-axis)
V_ANGLE_DEG     = -88.3       # vertical   grid line tilt
H_SPACING       = 180         # px between parallel horizontal lines
V_SPACING       = 180         # px between parallel vertical lines
BACKGROUND_LOW  = 80          # darkest background value (uint8)
BACKGROUND_HIGH = 200         # brightest background value (uint8)
BG_NOISE_SIGMA  = 12          # Gaussian noise added to the background
TOP_NOISE_SIGMA = 8           # lighter noise added after painting lines
SEED            = 42
# ---------------------------------------------------------------------------


def _draw_family(canvas: np.ndarray, angle_deg: float, spacing: int,
                 axis: str, thickness: int, color: int = 0) -> None:
    """Draw a family of parallel lines across *canvas* at *angle_deg* degrees.

    Args:
        canvas:    HxW uint8 array modified in-place.
        angle_deg: Line angle in degrees from the positive x-axis.
        spacing:   Distance (px) between consecutive lines, measured
                   perpendicular to the line direction.
        axis:      ``"h"`` → anchor lines along the y-axis (horizontal family);
                   ``"v"`` → anchor lines along the x-axis (vertical family).
        thickness: Line thickness in pixels.
        color:     Line intensity (0 = black).
    """
    H, W = canvas.shape[:2]
    rad = np.deg2rad(angle_deg)
    L = int(np.hypot(W, H)) + 1   # length that guarantees full-canvas coverage

    dx = int(round(L * np.cos(rad)))
    dy = int(round(L * np.sin(rad)))

    if axis == "h":
        for anchor in range(0, H + spacing, spacing):
            cx, cy = W // 2, anchor
            cv2.line(canvas, (cx - dx, cy - dy), (cx + dx, cy + dy),
                     color, thickness)
    else:
        for anchor in range(0, W + spacing, spacing):
            cx, cy = anchor, H // 2
            cv2.line(canvas, (cx - dx, cy - dy), (cx + dx, cy + dy),
                     color, thickness)


def generate(out_dir: Path) -> None:
    rng = np.random.default_rng(SEED)

    STEP = int(TILE_SIZE * (1.0 - OVERLAP))   # 460
    W = H = TILE_SIZE + (COLS - 1) * STEP     # 1432

    # --- background: diagonal gradient + Gaussian noise ---
    xx, yy = np.meshgrid(np.linspace(0.0, 1.0, W),
                         np.linspace(0.0, 1.0, H))
    gradient = BACKGROUND_LOW + (BACKGROUND_HIGH - BACKGROUND_LOW) * (xx + yy) / 2.0
    bg_noise = rng.normal(0.0, BG_NOISE_SIGMA, (H, W))
    canvas = np.clip(gradient + bg_noise, 0, 255).astype(np.uint8)

    # --- paint grid lines ---
    _draw_family(canvas, H_ANGLE_DEG, H_SPACING, axis="h", thickness=LINE_WIDTH)
    _draw_family(canvas, V_ANGLE_DEG, V_SPACING, axis="v", thickness=LINE_WIDTH)

    # --- add light surface noise on top ---
    top_noise = rng.normal(0.0, TOP_NOISE_SIGMA, (H, W))
    canvas = np.clip(canvas.astype(np.float32) + top_noise, 0, 255).astype(np.uint8)

    # --- slice into overlapping tiles ---
    out_dir.mkdir(parents=True, exist_ok=True)
    series = 0
    for col in range(COLS):
        for row in range(ROWS):
            x0, y0 = col * STEP, row * STEP
            tile = canvas[y0 : y0 + TILE_SIZE, x0 : x0 + TILE_SIZE]
            fname = out_dir / f"TileScan_001_s{series:03d}_ch00.tif"
            tifffile.imwrite(str(fname), tile, compression="lzw")
            print(f"  wrote {fname.name}  (col={col}, row={row})")
            series += 1

    print(f"\n{COLS * ROWS} tiles written to {out_dir}/")


if __name__ == "__main__":
    generate(Path(__file__).parent / "tiles")
