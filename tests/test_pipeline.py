import numpy as np

from src.core.pipeline_service import PipelineService, build_passthrough_pipeline


def test_passthrough_pipeline_has_one_step(minimal_config):
    service = PipelineService(minimal_config, pipeline_factory=build_passthrough_pipeline)
    assert len(service.pipeline.steps) == 1
    assert service.pipeline.steps[0].name == "img_conversion"


def test_passthrough_pipeline_returns_rgb_array(minimal_config, gray_image):
    service = PipelineService(minimal_config, pipeline_factory=build_passthrough_pipeline)
    result = service.run(gray_image)
    assert result is not None
    assert isinstance(result.image, np.ndarray)
    # ImgConversionStep with mode=RGB promotes grayscale to 3-channel
    assert result.image.shape == (64, 64, 3)
