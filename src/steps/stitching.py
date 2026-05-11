from __future__ import annotations

import os
import re
import subprocess
from glob import glob
from typing import Any

from src.core.step_result import StepResult
from src.config import StitchingConfig
from src.core.step import PipelineStep


class StitchingStep(PipelineStep):
    """Stitch processed tiles into a single OME-TIFF using Ashlar."""

    def __init__(self, config: StitchingConfig) -> None:
        """Initialize the stitching step with configuration.

        Args:
            config: Stitching configuration specifying Ashlar parameters
                such as file pattern, tile grid dimensions, and output
                file name.
        """
        super().__init__(name="stitching", config=config)

    def run(self, data: Any) -> StepResult:
        """Run Ashlar to stitch tiles into a single OME-TIFF.

        Args:
            data: Either a directory containing tiles or a list of tile
                file paths.

        Returns:
            :class:`~api.schemas.StepResult` with the output path and metadata.
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
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            self.error(f"Ashlar failed: {e.stderr.decode().strip()}")
            raise

        metadata = {"tiles": len(tiles)}
        return StepResult.from_data(output_path, metadata)