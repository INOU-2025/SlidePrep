from __future__ import annotations

import os
import subprocess
from glob import glob
from typing import Any, Optional

from src.core.step import PipelineStep
from config.config_schema import StitchingConfig


class StitchingStep(PipelineStep):
    """Stitch processed tiles into a single OME-TIFF using Ashlar."""

    def __init__(self, config: StitchingConfig, **kwargs: Any) -> None:
        """Initialize the stitching step with configuration.

        Args:
            config: Stitching configuration specifying output file name
                and tile search pattern.
            **kwargs: Optional keyword arguments forwarded to
                :class:`PipelineStep`.
        """
        super().__init__(name="stitching", config=config, **kwargs)

    def run(self, data: Any) -> tuple[str, Optional[dict]]:
        """Run Ashlar to stitch tiles into a single OME-TIFF.

        Args:
            data: Either a directory containing tiles or a list of tile
                file paths.

        Returns:
            Tuple containing the path to the stitched OME-TIFF and
            metadata with the number of tiles processed.
        """
        if isinstance(data, (list, tuple)):
            tiles = list(data)
            if not tiles:
                raise ValueError("No tiles provided for stitching")
            tile_dir = os.path.dirname(tiles[0])
        elif isinstance(data, str):
            tile_dir = data
            pattern = os.path.join(tile_dir, self.config.tile_glob)
            tiles = sorted(glob(pattern))
        else:
            raise TypeError("data must be a directory path or list of paths")

        if not tiles:
            raise ValueError(
                f"No tiles found using pattern {self.config.tile_glob} in {tile_dir}"
            )

        output_path = (
            self.config.output_filename
            if os.path.isabs(self.config.output_filename)
            else os.path.join(tile_dir, self.config.output_filename)
        )

        cmd = ["ashlar", *tiles, "-o", output_path]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            self.error(f"Ashlar failed: {e.stderr.decode().strip()}")
            raise

        metadata = {"tiles": len(tiles)}
        return output_path, metadata
