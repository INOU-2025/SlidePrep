"""Unit tests for the pure geometry helpers in GridRefinementStep.

These exercise _edge_unit_vector, _expand_min_rect, _set_short_side_even and
_set_short_side_uneven directly, without loading the RF classifier model,
since none of them touch self.config/self.model. A bare instance is built
via object.__new__ to skip GridRefinementStep.__init__ (which calls
joblib.load).

Regression coverage: image_shape is stored as (width, height) throughout the
pipeline (see PipelineContext.image_shape), but these helpers previously
unpacked it as `H, W = image_shape[:2]` — swapping width and height for any
non-square tile. All tests below use a deliberately non-square image_shape
so a reintroduced swap would fail them.
"""

import pytest

from src.steps.grid_refinement import (
    GridRefinementStep,
    _edge_unit_vector,
)
from src.utils.detection.models import DetectionRegion, Orientation

NON_SQUARE_SHAPE = (300, 100)  # (width=300, height=100)


def _step() -> GridRefinementStep:
    """Build a GridRefinementStep instance without running __init__."""
    return object.__new__(GridRefinementStep)


class TestEdgeUnitVectorZones:
    def test_horizontal_top_zone(self):
        v = _edge_unit_vector(Orientation.HORIZONTAL, NON_SQUARE_SHAPE, (0, 0), DetectionRegion.TOP)
        assert list(v) == [0.0, -1.0]

    def test_horizontal_bottom_zone(self):
        v = _edge_unit_vector(Orientation.HORIZONTAL, NON_SQUARE_SHAPE, (0, 0), DetectionRegion.BOTTOM)
        assert list(v) == [0.0, 1.0]

    def test_vertical_left_zone(self):
        v = _edge_unit_vector(Orientation.VERTICAL, NON_SQUARE_SHAPE, (0, 0), DetectionRegion.LEFT)
        assert list(v) == [-1.0, 0.0]

    def test_vertical_right_zone(self):
        v = _edge_unit_vector(Orientation.VERTICAL, NON_SQUARE_SHAPE, (0, 0), DetectionRegion.RIGHT)
        assert list(v) == [1.0, 0.0]


class TestEdgeUnitVectorFallback:
    """zone=None fallback compares the centroid against the real width/height."""

    def test_horizontal_fallback_uses_height_not_width(self):
        # width=300, height=100 -> H*0.5=50. cy=80 is below the real
        # midline (bottom half) but above the swapped midline (300*0.5=150),
        # so a width/height swap would flip the result.
        v = _edge_unit_vector(Orientation.HORIZONTAL, NON_SQUARE_SHAPE, (150, 80), None)
        assert list(v) == [0.0, 1.0]  # bottom

    def test_vertical_fallback_uses_width_not_height(self):
        # width=300, height=100 -> W*0.5=150. cx=80 is left of the real
        # midline but right of the swapped midline (100*0.5=50).
        v = _edge_unit_vector(Orientation.VERTICAL, NON_SQUARE_SHAPE, (80, 50), None)
        assert list(v) == [-1.0, 0.0]  # left


class TestExpandMinRect:
    def test_horizontal_expands_by_width(self):
        step = _step()
        min_rect = ((150.0, 50.0), (20.0, 5.0), 0.0)
        (cx, cy), (w, h), angle = step._expand_min_rect(min_rect, Orientation.HORIZONTAL, NON_SQUARE_SHAPE)
        assert w == pytest.approx(300 * GridRefinementStep.EXPANSION_FACTOR)
        assert h == pytest.approx(5.0)
        assert (cx, cy) == (150.0, 50.0)
        assert angle == 0.0

    def test_vertical_expands_by_height(self):
        step = _step()
        min_rect = ((150.0, 50.0), (5.0, 20.0), 0.0)
        (cx, cy), (w, h), angle = step._expand_min_rect(min_rect, Orientation.VERTICAL, NON_SQUARE_SHAPE)
        assert w == pytest.approx(5.0)
        assert h == pytest.approx(100 * GridRefinementStep.EXPANSION_FACTOR)
        assert (cx, cy) == (150.0, 50.0)
        assert angle == 0.0


class TestSetShortSideEven:
    def test_wide_rect_grows_height(self):
        step = _step()
        min_rect = ((10.0, 10.0), (40.0, 10.0), 0.0)
        (cx, cy), (w, h), angle = step._set_short_side_even(min_rect, Orientation.HORIZONTAL, 48)
        assert (cx, cy) == (10.0, 10.0)
        assert w == 40.0
        assert h == 48.0

    def test_tall_rect_grows_width(self):
        step = _step()
        min_rect = ((10.0, 10.0), (10.0, 40.0), 0.0)
        (cx, cy), (w, h), angle = step._set_short_side_even(min_rect, Orientation.VERTICAL, 48)
        assert (cx, cy) == (10.0, 10.0)
        assert w == 48.0
        assert h == 40.0


class TestSetShortSideUneven:
    def test_bias_half_keeps_center_fixed(self):
        step = _step()
        min_rect = ((100.0, 100.0), (40.0, 10.0), 0.0)
        (cx, cy), (w, h), _ = step._set_short_side_uneven(
            min_rect, Orientation.HORIZONTAL, target_thickness=20,
            image_shape=NON_SQUARE_SHAPE, zone=DetectionRegion.BOTTOM, bias=0.5,
        )
        assert (cx, cy) == pytest.approx((100.0, 100.0))
        assert (w, h) == pytest.approx((40.0, 20.0))

    def test_bias_shifts_center_toward_bottom_edge(self):
        step = _step()
        min_rect = ((100.0, 100.0), (40.0, 10.0), 0.0)
        (cx, cy), (w, h), _ = step._set_short_side_uneven(
            min_rect, Orientation.HORIZONTAL, target_thickness=20,
            image_shape=NON_SQUARE_SHAPE, zone=DetectionRegion.BOTTOM, bias=0.6,
        )
        # d_total = 20 - 10 = 10; delta_c = (0.6 - 0.5) * 10 = 1.0 toward BOTTOM (+y)
        assert cx == pytest.approx(100.0)
        assert cy == pytest.approx(101.0)
        assert (w, h) == pytest.approx((40.0, 20.0))

    def test_bias_shifts_center_toward_top_edge(self):
        step = _step()
        min_rect = ((100.0, 100.0), (40.0, 10.0), 0.0)
        (cx, cy), (w, h), _ = step._set_short_side_uneven(
            min_rect, Orientation.HORIZONTAL, target_thickness=20,
            image_shape=NON_SQUARE_SHAPE, zone=DetectionRegion.TOP, bias=0.6,
        )
        assert cx == pytest.approx(100.0)
        assert cy == pytest.approx(99.0)
