"""Shared per-run state passed through the pipeline."""

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class PipelineContext:
    """Shared runtime state for pipeline execution.

    Attributes:
        input_image_path: Path of the image currently being processed.
        image_shape: Width and height of the current image (``width``, ``height``).
        original_image: Original image array currently being processed.
        inpaint_mask: Binary mask (nonzero = reconstructed) produced by
            ``MaskCreationStep`` for the current tile, if grid removal ran.
    """
    input_image_path: Optional[str] = None
    image_shape: Optional[tuple[int, int]] = None
    original_image: np.ndarray | None = None
    inpaint_mask: np.ndarray | None = None