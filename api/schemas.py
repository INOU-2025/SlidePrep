"""Pydantic models exposed through the API layer."""

from pydantic import BaseModel

from config.config_schema import (
    GeneralConfig,
    TestConfig,
    ImgConversionConfig,
    BinarizationConfig,
    GridDetectionConfig,
    GridRefinementConfig,
    InpaintingConfig,
    StitchingConfig,
    LogConfig,
    DebugConfig,
)


class AppConfig(BaseModel):
    """Composite application configuration used by API endpoints."""

    general: GeneralConfig
    test: TestConfig | None = None
    img_conversion: ImgConversionConfig | None = None
    binarization: BinarizationConfig | None = None
    grid_detection: GridDetectionConfig | None = None
    grid_refinement: GridRefinementConfig | None = None
    inpainting: InpaintingConfig | None = None
    stitching: StitchingConfig = StitchingConfig()
    log: LogConfig = LogConfig()
    debug: DebugConfig = DebugConfig()