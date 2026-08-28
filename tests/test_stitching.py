"""Tests for StitchingStep's tile-count guard and the underlying position-counting helper."""

from unittest.mock import patch, MagicMock

import pytest

from src.config.schema import StitchingConfig
from src.steps.stitching import StitchingStep
from src.utils.stitching_utils import count_tile_positions

PATTERN = "TileScan_001_s{series:3}_ch{channel:2}.tif"


def _write_tiles(tmp_path, num_positions: int, num_channels: int) -> list[str]:
    """Writes num_positions x num_channels empty placeholder files matching PATTERN.
    The guard only ever inspects filenames, never opens image content, so
    empty files are sufficient."""
    paths = []
    for series in range(num_positions):
        for channel in range(num_channels):
            p = tmp_path / f"TileScan_001_s{series:03d}_ch{channel:02d}.tif"
            p.touch()
            paths.append(str(p))
    return paths


def test_count_tile_positions_multi_channel(tmp_path):
    """4 positions x 2 channels = 8 files must collapse to 4 positions, not 8."""
    paths = _write_tiles(tmp_path, num_positions=4, num_channels=2)
    assert len(paths) == 8
    assert count_tile_positions(paths, PATTERN) == 4


def test_stitching_step_raises_on_tile_count_mismatch(tmp_path):
    """3 real positions against a declared 2x2=4 grid must abort loudly, naming
    the found count and the declared width/height, before ever invoking ashlar."""
    _write_tiles(tmp_path, num_positions=3, num_channels=1)
    config = StitchingConfig(pattern=PATTERN, width=2, height=2)
    step = StitchingStep(config)

    with patch("src.steps.stitching.subprocess.run") as mock_run:
        with pytest.raises(ValueError) as exc_info:
            step.run(str(tmp_path))
        mock_run.assert_not_called()

    message = str(exc_info.value)
    assert "3 tile position" in message
    assert "stitching.width=2" in message
    assert "stitching.height=2" in message


def test_stitching_step_passes_guard_on_matching_multi_channel_grid(tmp_path):
    """4 positions x 2 channels against a declared 2x2=4 grid must NOT raise
    from the guard — proves the guard doesn't misfire on a legitimate
    multi-channel acquisition. subprocess.run is mocked since this only
    tests the guard, not a real ashlar invocation."""
    _write_tiles(tmp_path, num_positions=4, num_channels=2)
    config = StitchingConfig(pattern=PATTERN, width=2, height=2)
    step = StitchingStep(config)

    fake_completed = MagicMock(returncode=0)
    with patch("src.steps.stitching.subprocess.run", return_value=fake_completed) as mock_run:
        with patch("src.steps.stitching.inject_physical_size"):
            step.run(str(tmp_path))
        mock_run.assert_called_once()
