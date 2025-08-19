import os
from typing import Optional, List, Dict, Any, IO

from pydantic import BaseModel, Field, field_validator, model_validator


class GeneralConfig(BaseModel):
    """
    General configuration properties that apply across all pipeline operations.

    Defines common settings for input/output paths, file filtering, and
    operational modes that are used throughout the SlidePrep processing
    pipeline. Provides validation to ensure paths exist and settings are
    coherent before processing begins.
    """

    input_path: str = ""  # Source file or directory path
    output_path: str = "output"  # Destination directory for results
    suffix_filter: str = ""  # File suffix filter for batch processing
    output_suffix: str = ""  # Suffix added to output filenames
    log: bool = True  # Enable logging operations
    debug: bool = False  # Enable debug mode with additional output

    @field_validator("input_path")
    @classmethod
    def _validate_input_path(cls, v: str) -> str:
        """Ensure the input path exists when provided."""
        if v and not os.path.exists(v):
            raise ValueError(f"Input path does not exist: {v}")
        return v


class TestConfig(BaseModel):
    """Configuration overrides used when running isolated tests."""

    input_path: str = ""  # Path containing test images
    output_path: str = ""  # Directory where test results are written
    input_type: str = "image"  # "image" or "data"
    max_images: Optional[int] = None  # Maximum number of images to process

    @field_validator("input_path")
    @classmethod
    def _validate_input_path(cls, v: str) -> str:  # pragma: no cover - simple validation
        if v and not os.path.exists(v):
            raise ValueError(f"Test input path does not exist: {v}")
        return v

    @field_validator("input_type")
    @classmethod
    def _validate_input_type(cls, v: str) -> str:
        valid_types = {"image", "data"}
        if v not in valid_types:
            raise ValueError(f"input_type must be one of {valid_types}, got: {v}")
        return v

    @field_validator("max_images")
    @classmethod
    def _validate_max_images(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("max_images must be a positive integer")
        return v


class ImgConversionConfig(BaseModel):
    """Configuration for image format and mode conversion."""

    format: str = "png"
    mode: str = "RGB"

    @field_validator("format")
    @classmethod
    def _validate_format(cls, v: str) -> str:
        valid_formats = {"jpeg", "png", "tiff"}
        if v.lower() not in valid_formats:
            raise ValueError(
                f"Invalid format: {v}. "
                f"Valid formats: {', '.join(sorted(valid_formats))}"
            )
        return v

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, v: str) -> str:
        valid_modes = {"rgb", "grayscale", "greyscale"}
        if v.lower() not in valid_modes:
            raise ValueError("Invalid mode: {v}. Valid modes: RGB, Greyscale")
        return v


class BinarizationConfig(BaseModel):
    """
    Configuration for image binarization processing step.

    Specifies the thresholding method to use for converting grayscale
    images to binary format. Supports both adaptive and global thresholding
    algorithms with automatic parameter selection or custom optimization.
    """

    threshold_method: str = "combined_differential"  # Binarization algorithm name

    @field_validator("threshold_method")
    @classmethod
    def _validate_threshold_method(cls, v: str) -> str:
        """Validate binarization method selection."""
        valid_methods = {
            "otsu",
            "triangle",
            "li",
            "yen",
            "isodata",
            "minimum",
            "combined_differential",
            "adaptive_gaussian",
            "adaptive_mean",
        }
        if v.lower() not in valid_methods:
            raise ValueError(
                f"Invalid threshold method: {v}. "
                f"Valid methods: {', '.join(sorted(valid_methods))}"
            )
        return v


class GridDetectionConfig(BaseModel):
    """
    Configuration for adaptive grid detection.

    Contains all adaptive detector settings directly without extra nesting.
    """

    # Global template matching settings
    threshold: float = 0.1
    angles: List[float] = Field(default_factory=lambda: [2.0, -2.0])

    # Performance optimizations
    enable_early_exit: bool = True
    enable_template_cache: bool = True
    enable_preprocessing_cache: bool = True
    cache_max_size: int = 50

    # Strategy configurations - must be provided in JSON
    general: Dict[str, Any]
    thick_border: Dict[str, Any]
    thin_border: Dict[str, Any]

    @model_validator(mode="after")
    def _validate_settings(cls, values: "GridDetectionConfig") -> "GridDetectionConfig":
        """Validate settings and ensure all required configurations are provided."""
        if values.cache_max_size <= 0:
            raise ValueError("cache_max_size must be positive")

        if not 0 <= values.threshold <= 1:
            raise ValueError(
                f"threshold must be between 0 and 1, got: {values.threshold}"
            )
        if not values.angles:
            raise ValueError("angles cannot be empty")
        for angle in values.angles:
            if not -45 <= angle <= 45:
                raise ValueError(
                    f"angles must be between -45 and 45 degrees, got: {angle}"
                )

        cls._validate_strategy_config("general", values.general, False)
        cls._validate_strategy_config("thick_border", values.thick_border, True)
        cls._validate_strategy_config("thin_border", values.thin_border, True)
        return values

    @staticmethod
    def _validate_strategy_config(name: str, config: Dict[str, Any], border_required: bool) -> None:
        """Validate a strategy configuration dictionary."""
        if border_required:
            required_keys = {
                "template_length",
                "thickness",
                "border_thickness",
                "min_contour_area",
            }
        else:
            required_keys = {"template_length", "thickness", "min_contour_area"}

        if not all(key in config for key in required_keys):
            missing = required_keys - set(config.keys())
            raise ValueError(f"{name} strategy missing required keys: {missing}")

        if config["template_length"] <= 0:
            raise ValueError(f"{name}.template_length must be positive")
        if config["thickness"] < 7:
            raise ValueError(f"{name}.thickness must be at least 7")
        if config["min_contour_area"] <= 0:
            raise ValueError(f"{name}.min_contour_area must be positive")

        if border_required and config["border_thickness"] < 0:
            raise ValueError(f"{name}.border_thickness must be non-negative")


class GridRefinementClassifierConfig(BaseModel):
    """Classifier configuration for grid refinement."""

    model_path: str = ""
    features: List[str] = Field(..., min_length=1)
    threshold: float = 0.5

    @field_validator("model_path")
    @classmethod
    def _validate_model_path(cls, v: str) -> str:
        if v and not os.path.isfile(v):
            raise ValueError(f"classifier.model_path does not exist: {v}")
        return v

    @field_validator("threshold")
    @classmethod
    def _validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("classifier.threshold must be between 0 and 1")
        return v


class GridRefinementConfig(BaseModel):
    """Configuration for grid refinement step."""

    classifier: GridRefinementClassifierConfig = Field(
        default_factory=GridRefinementClassifierConfig
    )
    target_inclination_angles: Dict[str, float] = Field(default_factory=dict)
    target_thickness: int = 22
    thickness_bias: float = 0.90

    @model_validator(mode="after")
    def _validate_settings(cls, values: "GridRefinementConfig") -> "GridRefinementConfig":
        if values.target_inclination_angles:
            required_keys = {"horizontal", "vertical", "tolerance"}
            missing = required_keys - set(values.target_inclination_angles.keys())
            if missing:
                raise ValueError(
                    f"target_inclination_angles missing keys: {missing}")
            for k, v in values.target_inclination_angles.items():
                if not isinstance(v, (float, int)):
                    raise ValueError(
                        f"target_inclination_angles[{k}] must be a float")
        if not isinstance(values.target_thickness, int) or values.target_thickness <= 0:
            raise ValueError("target_thickness must be a positive integer")
        if not 0.0 <= values.thickness_bias <= 1.0:
            raise ValueError("thickness_bias must be between 0 and 1")
        return values


class InpaintingConfig(BaseModel):
    """Configuration for mask-based inpainting step."""

    model: str = "lama"  # Inpainting algorithm identifier
    mask_path: str = ""  # Directory containing mask images
    mask_suffix: str = "_mask"  # Suffix appended to filename to locate mask

    @field_validator("model")
    @classmethod
    def _validate_model(cls, v: str) -> str:
        valid_models = {"lama"}
        if v.lower() not in valid_models:
            raise ValueError(
                f"Invalid inpainting model: {v}. "
                f"Valid models: {', '.join(sorted(valid_models))}"
            )
        return v

    @field_validator("mask_path")
    @classmethod
    def _validate_mask_path(cls, v: str) -> str:
        if v and not os.path.isdir(v):
            raise ValueError(f"mask_path does not exist: {v}")
        return v


class StitchingConfig(BaseModel):
    """Configuration for whole slide stitching step."""
    output_filename: str = "stitched_slide.ome.tif"  # Name of generated OME-TIFF
    pattern: str = "TileScan_001_s{series:3}_ch{channel:2}.tiff"  # File pattern used by Ashlar
    overlap: float = 0.1  # Fractional tile overlap for registration
    pixel_size: float = 1.0  # Physical pixel size in microns
    width: int = 1  # Tile grid width
    height: int = 1  # Tile grid height
    layout: str = "raster"  # Acquisition layout
    direction: str = "horizontal"  # Raster direction

    @model_validator(mode="after")
    def _validate_settings(cls, values: "StitchingConfig") -> "StitchingConfig":
        """Validate stitching configuration parameters."""
        if not values.output_filename:
            raise ValueError("output_filename must be specified")
        if not values.pattern:
            raise ValueError("pattern must be specified")
        if not 0 <= values.overlap < 1:
            raise ValueError("overlap must be between 0 and 1")
        if values.pixel_size <= 0:
            raise ValueError("pixel_size must be positive")
        if values.width <= 0 or values.height <= 0:
            raise ValueError("width and height must be positive integers")
        return values


class DebugConfig(BaseModel):
    """Debug configuration for controlling artifact generation."""

    relative_path: Optional[str] = None  # Location inside the run's output directory
    saved_artifact_type: str = "image"  # "image", "data", or "both"
    save_composite_img: bool = False  # Generate composite visualization images
    save_aggregated_data: bool = False  # Persist aggregated results
    input_result_file_name: Optional[str] = None
    result_file_name: str = "aggregated_data.json"
    path: str = ""
    artifact_sink: str = "local"  # "local" or "memory"

    @field_validator("saved_artifact_type")
    @classmethod
    def _validate_saved_artifact_type(cls, v: str) -> str:  # pragma: no cover - simple validation
        valid_types = {"image", "data", "both"}
        if v not in valid_types:
            raise ValueError(
                "saved_artifact_type must be one of 'image', 'data', or 'both'"
            )
        return v

    @field_validator("artifact_sink")
    @classmethod
    def _validate_artifact_sink(cls, v: str) -> str:  # pragma: no cover - simple validation
        valid_sinks = {"local", "memory"}
        if v not in valid_sinks:
            raise ValueError(
                f"artifact_sink must be one of {valid_sinks}, got: {v}"
            )
        return v


class LogConfig(BaseModel):
    """Configuration for application logging system.

    Supports file-based and stream-based logging. When ``stream`` is
    provided it takes precedence over writing to a file, enabling use in
    environments without filesystem access.
    """

    log_to_file: bool = False
    log_to_console: bool = True
    log_file_name: str = "app.log"
    log_level: str = "INFO"
    stream: Optional[IO[str]] = Field(default=None, repr=False)
    relative_path: Optional[str] = None
    path: str = ""

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:  # pragma: no cover - simple validation
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(
                f"Invalid log level: {v}. "
                f"Valid levels: {', '.join(sorted(valid_levels))}"
            )
        return v.upper()
