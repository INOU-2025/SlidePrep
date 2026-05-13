from __future__ import annotations

"""High-level service for executing the processing pipeline on an image."""

from typing import Callable, Optional, TYPE_CHECKING

import asyncio
import numpy as np

from src.core.bootstrap import bootstrap
from src.core.app_config_manager import AppConfigManager
from src.core.container import Container
from src.core.pipeline import Pipeline
from src.core.step_result import StepResult

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from api import AppConfig


def build_default_pipeline(config: AppConfigManager, container: Container) -> Pipeline:
    """Single source of truth for the default 6-step pipeline sequence."""
    from src.steps import (
        BinarizationStep,
        GridDetectionStep,
        GridRefinementStep,
        MaskCreationStep,
        InpaintingStep,
        ImgConversionStep,
    )
    steps = [
        BinarizationStep(config=config.binarization_config),
        GridDetectionStep(config=config.grid_detection_config),
        GridRefinementStep(config.grid_refinement_config),
        MaskCreationStep(),
        InpaintingStep(config=config.inpainting_config),
        ImgConversionStep(config=config.img_conversion_config),
    ]
    return Pipeline(steps, container)


class PipelineService:
    """Service that runs the configured step chain on image data."""

    def __init__(
        self,
        config_path: str | None = None,
        *,
        config: AppConfigManager | "AppConfig" | None = None,
        image_shape: tuple[int, int] | None = None,
        pipeline_factory: Callable[[AppConfigManager, Container], Pipeline] | None = None,
    ) -> None:
        """Initialize the service from a path or configuration object.

        Args:
            config_path: Path to the JSON configuration file.
            config: Pre-loaded configuration object to use directly.
            image_shape: Optional width and height of the input image.
            pipeline_factory: Optional callable that builds the Pipeline.
                Receives the resolved ``AppConfigManager`` and ``Container``.
                Defaults to :func:`build_default_pipeline`.

        Raises:
            ValueError: If neither ``config_path`` nor ``config`` is provided.
        """
        if config is None and not config_path:
            raise ValueError("Either config_path or config must be provided")

        self.container = bootstrap(config_path, config=config, image_shape=image_shape)
        self.config: AppConfigManager = self.container.resolve("config")
        self.context = self.container.resolve("pipeline_context")
        self.logger = self.container.resolve("logger")
        self._pipeline_factory = pipeline_factory
        self.pipeline = self._create_pipeline()

    def _prepare_context(
        self, image: np.ndarray, image_path: Optional[str]
    ) -> None:
        """Validate the image and populate context metadata.

        The original image array is stored in the pipeline context for later
        steps that require access to the unmodified source image.

        Args:
            image: Input image array.
            image_path: Optional path for logging/debugging.

        Raises:
            ValueError: If the image is empty or missing dimensions.
        """
        if image.size == 0:
            raise ValueError("Input image is empty")
        if image.ndim < 2 or image.shape[0] == 0 or image.shape[1] == 0:
            raise ValueError("Input image dimensions are missing")

        self.context.original_image = image
        self.context.image_shape = (image.shape[1], image.shape[0])
        if image_path is not None:
            self.context.input_image_path = image_path

    def _create_pipeline(self) -> Pipeline:
        factory = self._pipeline_factory or build_default_pipeline
        pipeline = factory(self.config, self.container)
        if self.logger:
            self.logger.info(f"Pipeline initialized with {len(pipeline.steps)} steps")
        return pipeline

    def run(self, image: np.ndarray, *, image_path: Optional[str] = None, on_step_start: Optional[callable] = None) -> StepResult:
        """Process a single image through the pipeline.

        Args:
            image: Input image array.
            image_path: Optional path to the image for logging purposes.
            on_step_start: Optional callback for step start notifications.

        Returns:
            :class:`~src.core.step_result.StepResult` from the last pipeline step.

        Raises:
            ValueError: If the image is empty or lacks dimensions.
        """
        self._prepare_context(image, image_path)
        return self.pipeline.run(image, on_step_start=on_step_start)

    def stitch(self, processed_dir: str) -> StepResult:
        """Stitch a directory of processed tiles into a single OME-TIFF.

        Args:
            processed_dir: Path to the directory containing processed tile images.

        Returns:
            :class:`~src.core.step_result.StepResult` with the output path and tile count metadata.
        """
        from src.steps import StitchingStep
        step = StitchingStep(config=self.config.stitching_config)
        step.container = self.container
        return step.run(processed_dir)

    async def run_async(
        self, image: np.ndarray, *, image_path: Optional[str] = None
    ) -> StepResult:
        """Asynchronously process a single image through the pipeline.

        Args:
            image: Input image array.
            image_path: Optional path to the image for logging purposes.

        Returns:
            :class:`~src.core.step_result.StepResult` from the last pipeline step.

        Raises:
            ValueError: If the image is empty or lacks dimensions.
        """
        self._prepare_context(image, image_path)
        return await asyncio.to_thread(self.pipeline.run, image)


def run_pipeline(
    image: np.ndarray,
    config_path: str | None = None,
    *,
    config: AppConfigManager | "AppConfig" | None = None,
    image_path: Optional[str] = None,
) -> StepResult:
    """Process an image with a transient :class:`PipelineService` instance."""

    shape = (image.shape[1], image.shape[0])
    service = PipelineService(config_path, config=config, image_shape=shape)
    return service.run(image, image_path=image_path)


__all__ = ["PipelineService", "run_pipeline", "build_default_pipeline"]
