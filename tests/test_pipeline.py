"""Tests for PipelineService and the passthrough pipeline factory."""

import numpy as np

from src.core.pipeline_service import PipelineService, build_passthrough_pipeline


def test_passthrough_pipeline_has_one_step(minimal_config):
    service = PipelineService(minimal_config, pipeline_factory=build_passthrough_pipeline)
    assert len(service.pipeline.steps) == 1
    assert service.pipeline.steps[0].name == "img_conversion"


def test_passthrough_pipeline_returns_grayscale_array(minimal_config, gray_image):
    service = PipelineService(minimal_config, pipeline_factory=build_passthrough_pipeline)
    result = service.run(gray_image)
    assert result is not None
    assert isinstance(result.image, np.ndarray)
    # ImgConversionStep always normalises to grayscale (2D) now — StitchingStep/
    # Ashlar requires 2D tiles, so there's no config path that produces 3-channel
    # output anymore.
    assert result.image.shape == (64, 64)
