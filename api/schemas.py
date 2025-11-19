from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
from pydantic import BaseModel

from config.config_schema import (
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

StepResult = Union[np.ndarray, Tuple[np.ndarray, Dict[str, Any]]]