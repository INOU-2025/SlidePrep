from unittest.mock import MagicMock

import numpy as np

from src.config import InpaintingConfig
from src.core.container import build_container
from src.core.context import PipelineContext
from src.steps.inpainting import InpaintingStep


def test_inpainting_calls_model_with_rgb(gray_image, binary_mask):
    mock_model = MagicMock(return_value=np.ones((64, 64, 3), dtype=np.uint8))

    context = PipelineContext()
    context.original_image = gray_image  # 2D — InpaintingStep must promote to RGB

    container = build_container(context=context)
    # register_singleton calls callable providers, so use a factory lambda instead
    container.register_factory("simple_lama", lambda: mock_model)

    step = InpaintingStep(config=InpaintingConfig())
    step.container = container
    result = step.run(binary_mask)

    mock_model.assert_called_once()
    image_arg = mock_model.call_args[0][0]
    assert image_arg.ndim == 3 and image_arg.shape[2] == 3
    assert result.image is not None
