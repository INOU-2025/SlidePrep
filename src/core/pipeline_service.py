from __future__ import annotations

"""High-level service for executing the processing pipeline on an image."""

from typing import Any, Optional, TYPE_CHECKING

import numpy as np

from src.core import bootstrap
from src.core.pipeline import Pipeline
from src.core.app_config_manager import AppConfigManager

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from api import AppConfig
from src.steps import (
    BinarizationStep,
    GridDetectionStep,
    GridRefinementStep,
    MaskCreationStep,
    InpaintingStep,
    ImgConversionStep,
)


class PipelineService:
    """Service that runs the configured step chain on image data."""

    def __init__(
        self,
        config_path: str | None = None,
        *,
        config: AppConfigManager | "AppConfig" | None = None,
        image_shape: tuple[int, int] | None = None,
    ) -> None:
        """Initialize the service from a path or configuration object.

        Args:
            config_path: Path to the JSON configuration file.
            config: Pre-loaded configuration object to use directly.
            image_shape: Optional width and height of the input image.

        Raises:
            ValueError: If neither ``config_path`` nor ``config`` is provided.
        """
        if config is None and not config_path:
            raise ValueError("Either config_path or config must be provided")

        self.container = bootstrap(config_path, config=config, image_shape=image_shape)
        self.config: AppConfigManager = self.container.resolve("config")
        self.context = self.container.resolve("pipeline_context")
        self.logger = self.container.resolve("logger")
        self.pipeline = self._create_pipeline()

    def _create_pipeline(self) -> Pipeline:
        steps = [
            BinarizationStep(
                config=self.config.binarization_config, container=self.container),
            GridDetectionStep(
                config=self.config.grid_detection_config, container=self.container),
            GridRefinementStep(
                self.config.grid_refinement_config, container=self.container),
            MaskCreationStep(container=self.container),
            InpaintingStep(config=self.config.inpainting_config,
                           container=self.container),
            ImgConversionStep(
                config=self.config.img_conversion_config, container=self.container),
        ]
        if self.logger:
            self.logger.info(f"Pipeline initialized with {len(steps)} steps")
        return Pipeline(steps, self.container)

    def run(self, image: np.ndarray, *, image_path: Optional[str] = None) -> Any:
        """Process a single image through the pipeline.

        Args:
            image: Input image array.
            image_path: Optional path to the image for logging purposes.

        Returns:
            Processed image or a tuple of image and metadata.
        """
        self.context.image_shape = (image.shape[1], image.shape[0])
        if image_path is not None:
            self.context.input_image_path = image_path
        return self.pipeline.run(image)


def run_pipeline(
    image: np.ndarray,
    config_path: str | None = None,
    *,
    config: AppConfigManager | "AppConfig" | None = None,
    image_path: Optional[str] = None,
) -> Any:
    """Process an image with a transient :class:`PipelineService` instance."""

    shape = (image.shape[1], image.shape[0])
    service = PipelineService(config_path, config=config, image_shape=shape)
    return service.run(image, image_path=image_path)


__all__ = ["PipelineService", "run_pipeline"]
