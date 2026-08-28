"""Pipeline step that stitches processed tiles into a single OME-TIFF using Ashlar."""

from __future__ import annotations

import os
import re
import subprocess
from glob import glob
from typing import Any

from src.core.step_result import StepResult
from src.config import StitchingConfig
from src.core.step import PipelineStep
from src.utils.stitching_utils import inject_physical_size, count_tile_positions


class StitchingStep(PipelineStep):
    """Stitch processed tiles into a single OME-TIFF using Ashlar."""

    def __init__(self, config: StitchingConfig) -> None:
        super().__init__(name="stitching", config=config)

    def run(self, data: Any) -> StepResult:
        """Run Ashlar to stitch tiles into a single OME-TIFF.

        Args:
            data: Either a directory containing tiles or a list of tile
                file paths.

        Returns:
            :class:`~src.core.step_result.StepResult` with the output path and metadata.
        """
        if isinstance(data, (list, tuple)):
            paths = list(data)
            if not paths:
                raise ValueError("No tiles provided for stitching")
            tile_dir = os.path.dirname(paths[0])
        elif isinstance(data, str):
            tile_dir = data
        else:
            raise TypeError("data must be a directory path or list of paths")

        glob_pattern = re.sub(r"\{[^}]+\}", "*", self.config.pattern)
        pattern = os.path.join(tile_dir, glob_pattern)
        tiles = sorted(glob(pattern))
        if not tiles:
            raise ValueError(
                f"No tiles found using pattern {glob_pattern} in {tile_dir}"
            )

        num_positions = count_tile_positions(tiles, self.config.pattern)
        expected_positions = self.config.width * self.config.height
        if num_positions != expected_positions:
            raise ValueError(
                f"Tile count mismatch in {tile_dir}: found {num_positions} tile position(s) "
                f"({len(tiles)} file(s) across all channels), but stitching.width={self.config.width} "
                f"x stitching.height={self.config.height} declares {expected_positions} position(s). "
                "Ashlar's tile_rc() has no bounds validation and will silently assign wrong "
                "rows/columns to a mosaic assembled from this directory if this mismatch is ignored."
            )

        output_path = (
            self.config.output_filename
            if os.path.isabs(self.config.output_filename)
            else os.path.join(tile_dir, self.config.output_filename)
        )

        series_arg = (
            f"fileseries|{tile_dir}|pattern={self.config.pattern}"
            f"|overlap={self.config.overlap}"
            f"|pixel_size={self.config.pixel_size}"
            f"|width={self.config.width}"
            f"|height={self.config.height}"
            f"|layout={self.config.layout}"
            f"|direction={self.config.direction}"
        )

        cmd = ["ashlar", "--output", output_path, series_arg]
        if self.config.align_channel is not None:
            cmd.extend(["--align-channel", str(self.config.align_channel)])
        cmd.extend(["--maximum-shift", str(self.config.max_shift)])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            self.error(f"Ashlar failed: {e.stderr.decode().strip()}")
            raise

        inject_physical_size(output_path, self.config.pixel_size)

        metadata = {"tiles": len(tiles)}
        return StepResult.from_data(output_path, metadata)
