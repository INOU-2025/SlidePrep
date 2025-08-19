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

    def run(self, mask: Any) -> tuple[np.ndarray, Optional[dict]]:
        """Inpaint image regions defined by ``mask``.
        The source image is loaded from the pipeline context using
        ``input_image_path``. Only the mask is provided as input data.

        Parameters
        ----------
        mask: Any
            Binary mask where inpainted regions are marked.

        Returns
        -------
        tuple[np.ndarray, Optional[dict]]
            The inpainted image and optional metadata (``None``).
        """

        self._validate_image_input(mask)

        if not self.container:
            raise ValueError("Container not available for InpaintingStep")
        ctx = self.container.resolve("pipeline_context")
        image_path = ctx.input_image_path
        if not image_path:
            raise ValueError(
                "Pipeline context must contain 'input_image_path'")

        image = Image.open(image_path).convert("RGB")
        image = np.array(image)
        self._validate_image_input(image)

        result = self._model(image, mask)
        if isinstance(result, Image.Image):
            result = np.array(result)
        return result, None
