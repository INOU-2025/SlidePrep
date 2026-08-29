"""High-level service for executing the processing pipeline on an image."""

from __future__ import annotations

from typing import Callable, Optional, TYPE_CHECKING

import asyncio
import os

import cv2
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


def build_passthrough_pipeline(config: AppConfigManager, container: Container) -> Pipeline:
    """Pipeline for clean tiles: format conversion only, no grid removal."""
    from src.steps import ImgConversionStep
    steps = [ImgConversionStep(config=config.img_conversion_config)]
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
        self.context.inpaint_mask = None
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

    def log_step_summaries(self) -> None:
        """Let any step log a job-wide summary after all tiles have run.

        Call once, after the per-tile run() loop finishes for a job. Steps
        that accumulate per-tile state worth reporting in aggregate (e.g.
        GridRefinementStep's angle-correction-bound tally) implement
        log_summary(); steps that don't are silently skipped.
        """
        for step in self.pipeline.steps:
            summary_fn = getattr(step, "log_summary", None)
            if callable(summary_fn):
                summary_fn()

    def write_tile_mask(self, tile_output_path: str) -> Optional[str]:
        """Persist the most recent run()'s inpaint mask as a sidecar file, if any.

        Must be called immediately after ``run()`` for a given tile, before the
        next ``run()`` call resets the context. Writes a PNG named after the
        processed tile's own basename into an ``inpaint_masks`` subdirectory
        alongside it, so a later stitching pass can match sidecars back to
        tiles by filename.

        Args:
            tile_output_path: Path the processed tile image was written to.

        Returns:
            The path the mask sidecar was written to, or ``None`` if this
            tile produced no mask (e.g. ``--no-grid``, or a tile carried
            through raw without going through ``run()`` at all).
        """
        mask = self.context.inpaint_mask
        if mask is None:
            return None
        mask_dir = os.path.join(os.path.dirname(tile_output_path), "inpaint_masks")
        os.makedirs(mask_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(tile_output_path))[0]
        mask_path = os.path.join(mask_dir, f"{stem}.png")
        cv2.imwrite(mask_path, mask)
        return mask_path

    def stitch(self, processed_dir: str) -> StepResult:
        """Stitch a directory of processed tiles into a single OME-TIFF.

        Also composes the mosaic-space inpaint mask (if any per-tile masks
        were written during ``run()``/``write_tile_mask()`` for this job),
        chained after stitching the same way :class:`~src.core.pipeline.Pipeline`
        chains per-tile steps — this is the orchestration layer, so step
        sequencing lives here rather than in one step reaching into another.

        Args:
            processed_dir: Path to the directory containing processed tile images.

        Returns:
            :class:`~src.core.step_result.StepResult` with the output path and
            metadata (tile count, and ``inpaint_mask_path`` if a mask was written).
        """
        from src.steps import StitchingStep
        from src.utils.stitching_utils import write_inpaint_mask
        step = StitchingStep(config=self.config.stitching_config)
        step.container = self.container
        stitch_result = step.run(processed_dir)

        mask_path = write_inpaint_mask(processed_dir, stitch_result.data, self.config.stitching_config)

        metadata = {**stitch_result.metadata, "inpaint_mask_path": mask_path}
        return StepResult.from_data(stitch_result.data, metadata)

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


__all__ = ["PipelineService", "run_pipeline", "build_default_pipeline", "build_passthrough_pipeline"]
