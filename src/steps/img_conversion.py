"""Pipeline step that converts images to a target colour mode."""

from typing import Any

import numpy as np

from src.core.step_result import StepResult
from src.config import ImgConversionConfig
from src.core.step import PipelineStep
from src.utils.conversion_utils import validate_image_format
from src.utils.image_utils import convert_image_mode


class ImgConversionStep(PipelineStep):
    """Convert images to a specified format."""

    def __init__(self, config: ImgConversionConfig) -> None:
        super().__init__(name="img_conversion", config=config)
        self._format = validate_image_format(config.format)

    def run(self, data: Any) -> StepResult:
        """Convert input image according to the configuration.

        Args:
            data: Input image as a NumPy array.

        Returns:
            :class:`~src.core.step_result.StepResult` with the converted image and metadata.
        """
        self._validate_image_input(data)
        # Both entry points collapse any non-grayscale output back to grayscale
        # before writing (StitchingStep/Ashlar requires 2D tiles for TIFF), so
        # this step always normalises to grayscale rather than taking a mode
        # from config.
        converted = convert_image_mode(data, "grayscale")
        metadata = {"format": self._format}
        return StepResult.from_array(converted, metadata)