from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineContext:
    """Shared runtime state for pipeline execution.

    Attributes:
        input_image_path: Path of the image currently being processed.
        image_shape: Width and height of the current image.
    """
    input_image_path: Optional[str] = None
    image_shape: Optional[tuple[int, int]] = None