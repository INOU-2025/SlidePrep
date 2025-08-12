from typing import Any, Optional

import numpy as np
from PIL import Image
from simple_lama_inpainting import SimpleLama

from src.core.step import PipelineStep
from config.config_schema import InpaintingConfig


class InpaintingStep(PipelineStep):
    """Pipeline step for mask-based image inpainting."""

    def __init__(self, config: InpaintingConfig, **kwargs: Any) -> None:
        """Initialize inpainting step with specified model."""
        super().__init__(name="inpainting", config=config, **kwargs)

        model_name = self.config.model.lower()
        if model_name == "lama":
            self._model = SimpleLama()
        else:
            raise ValueError(
                f"Unsupported inpainting model: {self.config.model}")

    def run(self, data: Any) -> tuple[np.ndarray, Optional[dict]]:
        """Inpaint image regions defined by the mask."""
        if not isinstance(data, dict):
            raise TypeError(
                "InpaintingStep expects a dict with 'image' and 'mask' entries")

        image = data.get("image")
        mask = data.get("mask")
        if image is None or mask is None:
            raise ValueError(
                "Input dictionary must contain 'image' and 'mask'")

        self._validate_image_input(image)
        self._validate_image_input(mask)

        result = self._model(image, mask)
        if isinstance(result, Image.Image):
            result = np.array(result)
        return result, None