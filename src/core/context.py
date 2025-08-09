from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineContext:
    """Runtime context for pipeline execution."""
    input_image_path: Optional[str] = None
    image_shape: Optional[tuple[int, int]] = None