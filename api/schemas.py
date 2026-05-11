from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
from pydantic import BaseModel

from src.config import (
    GeneralConfig,
    TestConfig,
    BinarizationConfig,
    ImgConversionConfig,
    GridDetectionConfig,
    GridRefinementConfig,
    InpaintingConfig,
    StitchingConfig,
    LogConfig,
    DebugConfig,
)

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str = ""

class JobStatus(BaseModel):
    job_id: str
    status: str
    result_url: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None

class AppConfig(BaseModel):
    general: GeneralConfig
    test: Optional[TestConfig] = None
    img_conversion: Optional[ImgConversionConfig] = None
    binarization: Optional[BinarizationConfig] = None
    grid_detection: Optional[GridDetectionConfig] = None
    grid_refinement: Optional[GridRefinementConfig] = None
    inpainting: Optional[InpaintingConfig] = None
    stitching: Optional[StitchingConfig] = None
    log: Optional[LogConfig] = None
    debug: Optional[DebugConfig] = None

class StepResult:
    """
    Standardized result object for pipeline steps.
    Supports unpacking as (data, metadata) for backward compatibility.
    """
    def __init__(self, data: Any, metadata: Optional[Dict[str, Any]] = None):
        self.data = data
        self.metadata = metadata

    @classmethod
    def from_data(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "StepResult":
        return cls(data, metadata)

    @classmethod
    def from_array(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "StepResult":
        return cls(data, metadata)

    def to_array(self) -> Any:
        return self.data

    @property
    def image(self) -> Any:
        # Assuming data is the image if it's an ndarray, or None if not
        if isinstance(self.data, np.ndarray):
            return self.data
        return None

    def __iter__(self):
        yield self.data
        yield self.metadata