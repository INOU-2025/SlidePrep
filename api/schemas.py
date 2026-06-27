"""Pydantic request/response models for the SlidePrep API."""

from typing import Optional
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
from src.core.step_result import StepResult

class JobResponse(BaseModel):
    """Immediate acknowledgement returned after a job is queued."""
    job_id: str
    status: str
    message: str = ""

class JobStatus(BaseModel):
    """Full job state returned by the status-polling endpoint."""
    job_id: str
    status: str
    result_url: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    progress: Optional[int] = None
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    tile_count: Optional[int] = None

class AppConfig(BaseModel):
    """Complete pipeline configuration submitted as JSON in the request body."""
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

