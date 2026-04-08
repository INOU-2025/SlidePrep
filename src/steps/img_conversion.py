from typing import Any

import numpy as np

from api.schemas import StepResult
from src.config import ImgConversionConfig
from src.core.step import PipelineStep
from src.utils.conversion_utils import validate_image_format
from src.utils.image_utils import convert_image_mode


class ImgConversionStep(PipelineStep):
    """Convert images to a specified format and mode."""

    def __init__(self, config: ImgConversionConfig) -> None:
        """Initialize the conversion step with configuration.

        Args:
            config: Configuration defining target format and mode.
        """
        super().__init__(name="img_conversion", config=config)
        self._format = validate_image_format(config.format)
        self._mode = config.mode.upper()

    def run(self, data: Any) -> StepResult:
        """Convert input image according to the configuration.

        Args:
            data: Input image as a NumPy array.

        Returns:
            :class:`~api.schemas.StepResult` with the converted image and metadata.
        """
        self._validate_image_input(data)
        converted = convert_image_mode(data, self._mode)
        metadata = {"format": self._format, "mode": self._mode}
        return StepResult.from_array(converted, metadata)