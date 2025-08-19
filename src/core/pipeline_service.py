from __future__ import annotations

"""High-level service for executing the processing pipeline on an image."""

from typing import Any, Optional

import numpy as np

from src.core import bootstrap
from src.core.pipeline import Pipeline
from src.core.app_config_manager import AppConfigManager
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

    def __init__(self, config_path: str) -> None:
        """Initialize the service using the given configuration file.

        Args:
            config_path: Path to the JSON configuration file.
        """
        self.container = bootstrap(config_path)
        self.config: AppConfigManager = self.container.resolve("config")
        self.context = self.container.resolve("pipeline_context")
        self.logger = self.container.resolve("logger")
        self.pipeline = self._create_pipeline()

    def _create_pipeline(self) -> Pipeline:
        steps = [
            BinarizationStep(config=self.config.binarization_config, container=self.container),
            GridDetectionStep(config=self.config.grid_detection_config, container=self.container),
            GridRefinementStep(self.config.grid_refinement_config, container=self.container),
            MaskCreationStep(container=self.container),
            InpaintingStep(config=self.config.inpainting_config, container=self.container),
            ImgConversionStep(config=self.config.img_conversion_config, container=self.container),
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
        if image_path is not None:
            self.context.input_image_path = image_path
        return self.pipeline.run(image)


def run_pipeline(image: np.ndarray, config_path: str, *, image_path: Optional[str] = None) -> Any:
    """Process an image with a transient :class:`PipelineService` instance."""

    service = PipelineService(config_path)
    return service.run(image, image_path=image_path)


__all__ = ["PipelineService", "run_pipeline"]