from dataclasses import dataclass, field
import numpy as np
from typing import Optional, Dict

@dataclass
class PipelineContext:
    input_image: Optional[np.ndarray] = None
    image_path: Optional[str] = None
    image_name: Optional[str] = None
    gray_image: Optional[np.ndarray] = None
    binarized_image: Optional[np.ndarray] = None
    grid_lines: Optional[list] = None
    mask: Optional[np.ndarray] = None
    cleaned_image: Optional[np.ndarray] = None
    stitched_image: Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)