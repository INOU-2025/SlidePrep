"""Tests for mosaic-space inpaint mask composition across tile overlaps."""

import numpy as np

from src.utils.stitching_utils import compose_mosaic_mask


def test_compose_mosaic_mask_overlap_any_nonzero_wins():
    """Overlapping tiles disagree on one pixel; composition must OR, not overwrite."""
    tile_a = np.zeros((10, 10), dtype=np.uint8)
    tile_a[5, 8] = 255  # reconstructed at local (5,8) -> global (5,8)
    tile_b = np.zeros((10, 10), dtype=np.uint8)
    # placed at (0, 6): local (5,2) -> same global (5,8), tile_b says observed
    canvas = compose_mosaic_mask((10, 16), [(tile_a, (0, 0)), (tile_b, (0, 6))])

    assert canvas.shape == (10, 16)
    assert canvas.dtype == np.uint8
    assert set(np.unique(canvas)).issubset({0, 255})
    assert canvas[5, 8] == 255

    # Order-independence: OR is commutative, unlike pixel-intensity blending.
    canvas_reversed = compose_mosaic_mask((10, 16), [(tile_b, (0, 6)), (tile_a, (0, 0))])
    np.testing.assert_array_equal(canvas, canvas_reversed)


def test_compose_mosaic_mask_nonoverlap_regions_stay_observed():
    # tile_a global span [0,10), tile_b global span [6,16); overlap = global [6,10).
    tile_a = np.zeros((10, 10), dtype=np.uint8)
    tile_a[:, 0:6] = 255  # global [0,6) -- tile_a's exclusive footprint
    tile_b = np.zeros((10, 10), dtype=np.uint8)
    tile_b[:, 4:10] = 255  # local [4,10) -> global [10,16) -- tile_b's exclusive footprint
    canvas = compose_mosaic_mask((10, 16), [(tile_a, (0, 0)), (tile_b, (0, 6))])

    assert np.all(canvas[:, 0:6] == 255)    # tile_a's exclusive footprint
    assert np.all(canvas[:, 10:16] == 255)  # tile_b's exclusive footprint
    assert np.all(canvas[:, 6:10] == 0)     # overlap: neither tile marks it reconstructed


def test_compose_mosaic_mask_no_tiles_returns_empty_canvas():
    canvas = compose_mosaic_mask((10, 16), [])
    assert canvas.shape == (10, 16)
    assert canvas.dtype == np.uint8
    assert np.all(canvas == 0)
