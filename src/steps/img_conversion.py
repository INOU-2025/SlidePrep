from typing import Any, Optional
import numpy as np

from src.core.step import PipelineStep
from config.config_schema import ImgConversionConfig
from src.utils.image_utils import convert_image_mode
from src.utils.conversion_utils import validate_image_format


class ImgConversionStep(PipelineStep):
    """Convert images to a specified format and mode."""

    def __init__(self, config: ImgConversionConfig, **kwargs: Any) -> None:
        """Initialize the conversion step with configuration.

        Args:
            config: Configuration defining target format and mode.
            **kwargs: Optional keyword arguments forwarded to :class:`PipelineStep`.
        """
        super().__init__(name="img_conversion", config=config, **kwargs)
        self._format = validate_image_format(config.format)
        self._mode = config.mode.upper()

    def run(self, data: Any) -> tuple[np.ndarray, Optional[dict]]:
        """Convert input image according to the configuration.

        Args:
            data: Input image as a NumPy array.

        Returns:
            Tuple of the converted image and metadata containing the
            target format and mode.
        """
        self._validate_image_input(data)
        converted = convert_image_mode(data, self._mode)
        metadata = {"format": self._format, "mode": self._mode}
        return converted, metadata