from typing import Any

import numpy as np
from PIL import Image

from api.schemas import StepResult
from src.config import InpaintingConfig
from src.core.step import PipelineStep


class InpaintingStep(PipelineStep):
    """Pipeline step for mask-based image inpainting."""

    def __init__(self, config: InpaintingConfig, **kwargs: Any) -> None:
        """Initialize inpainting step with specified model."""
        super().__init__(name="inpainting", config=config, **kwargs)

        model_name = self.config.model.lower()
        if model_name == "lama":
            if not self.container:
                raise ValueError(
                    "Container not available for InpaintingStep")
            try:
                self._model = self.container.resolve("simple_lama")
            except KeyError as exc:
                raise ValueError(
                    "SimpleLama model not registered in container") from exc
        else:
            raise ValueError(
                f"Unsupported inpainting model: {self.config.model}")

    def run(self, mask: Any) -> StepResult:
        """Inpaint image regions defined by ``mask``.

        The source image is taken from ``PipelineContext.original_image`` when
        available. If the image array is not present in the context, the step
        falls back to loading the file specified by ``input_image_path``.

        Parameters
        ----------
        mask: Any
            Binary mask where inpainted regions are marked.

        Returns
        -------
        StepResult
            The inpainted image.
        """

        self._validate_image_input(mask)

        if not self.container:
            raise ValueError("Container not available for InpaintingStep")
        ctx = self.container.resolve("pipeline_context")
        image = ctx.original_image
        if image is None:
            image_path = ctx.input_image_path
            if not image_path:
                raise ValueError(
                    "Pipeline context must contain 'input_image_path' or 'original_image'")
            image = Image.open(image_path).convert("RGB")
            image = np.array(image)

        self._validate_image_input(image)

        # Ensure image is RGB (3 channels) for LaMa model
        if image.ndim == 2:
            self.debug(f"Converting 2D image {image.shape} to RGB")
            image = np.stack((image,) * 3, axis=-1)
        elif image.ndim == 3 and image.shape[2] == 1:
            self.debug(f"Converting 1-channel image {image.shape} to RGB")
            image = np.concatenate((image,) * 3, axis=2)
            
        self.debug(f"Inpainting inputs - Image: {image.shape} {image.dtype}, Mask: {mask.shape} {mask.dtype}")

        result = self._model(image, mask)
        if isinstance(result, Image.Image):
            result = np.array(result)
        return StepResult.from_array(result)

