from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineContext:
    """Runtime context for pipeline execution."""
    current_image_path: Optional[str] = None
