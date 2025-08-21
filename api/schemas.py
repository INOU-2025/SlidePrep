"""Pydantic models exposed through the API layer."""

from typing import Any, Dict

import numpy as np
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
from src.utils.serialization import array_to_base64, base64_to_array


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


class StepResult(BaseModel):
    """Standard pipeline step result with optional image and metadata."""

    image: str | None = None
    data: Any | None = None
    metadata: Dict[str, Any] | None = None

    @classmethod
    def from_array(
        cls, array: np.ndarray, metadata: Dict[str, Any] | None = None
    ) -> "StepResult":
        """Create a result from a NumPy array."""
        return cls(image=array_to_base64(array), metadata=metadata)

    @classmethod
    def from_data(
        cls, data: Any, metadata: Dict[str, Any] | None = None
    ) -> "StepResult":
        """Create a result from arbitrary data."""
        return cls(data=data, metadata=metadata)

    def to_array(self) -> np.ndarray | None:
        """Decode the embedded image back into a NumPy array."""
        if self.image is None:
            return None
        return base64_to_array(self.image)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result into JSON-serializable data."""
        result: Dict[str, Any] = {}
        if self.image is not None:
            result["image"] = self.image
        if self.data is not None:
            result["data"] = (
                self.data.tolist() if isinstance(self.data, np.ndarray) else self.data
            )
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result