from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, IO
import os


@dataclass
class GeneralConfig:
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

    def __post_init__(self) -> None:
        """
        Validate configuration after initialization.

        Raises:
            ValueError: If input_path is specified but does not exist
        """
        if self.input_path and not os.path.exists(self.input_path):
            raise ValueError(f"Input path does not exist: {self.input_path}")


@dataclass
class TestConfig:
    """Configuration overrides used when running isolated tests."""

    input_path: str = ""  # Path containing test images
    output_path: str = ""  # Directory where test results are written
    input_type: str = "image"  # "image" or "data"
    max_images: Optional[int] = None  # Maximum number of images to process

    def __post_init__(self) -> None:  # pragma: no cover - simple validation
        if self.input_path and not os.path.exists(self.input_path):
            raise ValueError(
                f"Test input path does not exist: {self.input_path}")
        valid_types = {"image", "data"}
        if self.input_type not in valid_types:
            raise ValueError(
                f"input_type must be one of {valid_types}, got: {self.input_type}"
            )
        if self.max_images is not None and self.max_images <= 0:
            raise ValueError("max_images must be a positive integer")


@dataclass
class ImgConversionConfig:
    """Configuration for image format and mode conversion."""

    format: str = "png"
    mode: str = "RGB"

    def __post_init__(self) -> None:
        valid_formats = {"jpeg", "png", "tiff"}
        valid_modes = {"rgb", "grayscale", "greyscale"}

        if self.format.lower() not in valid_formats:
            raise ValueError(
                f"Invalid format: {self.format}. "
                f"Valid formats: {', '.join(sorted(valid_formats))}"
            )
        if self.mode.lower() not in valid_modes:
            raise ValueError(
                f"Invalid mode: {self.mode}. Valid modes: RGB, Greyscale"
            )


@dataclass
class BinarizationConfig:
    """
    Configuration for image binarization processing step.

    Specifies the thresholding method to use for converting grayscale
    images to binary format. Supports both adaptive and global thresholding
    algorithms with automatic parameter selection or custom optimization.
    """

    threshold_method: str = "combined_differential"  # Binarization algorithm name

    def __post_init__(self) -> None:
        """
        Validate binarization method selection.

        Raises:
            ValueError: If threshold_method is not a supported algorithm
        """
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
        if self.threshold_method.lower() not in valid_methods:
            raise ValueError(
                f"Invalid threshold method: {self.threshold_method}. "
                f"Valid methods: {', '.join(sorted(valid_methods))}"
            )


@dataclass
class GridDetectionConfig:
    """
    Configuration for adaptive grid detection.

    Contains all adaptive detector settings directly without extra nesting.
    """

    # Global template matching settings
    threshold: float = 0.1
    angles: Optional[List[float]] = None

    # Performance optimizations
    enable_early_exit: bool = True
    enable_template_cache: bool = True
    enable_preprocessing_cache: bool = True
    cache_max_size: int = 50

    # Strategy configurations - must be provided in JSON
    general: Optional[Dict[str, Any]] = None
    thick_border: Optional[Dict[str, Any]] = None
    thin_border: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate settings and ensure all required configurations are provided."""
        if self.cache_max_size <= 0:
            raise ValueError(
                f"cache_max_size must be positive, got: {self.cache_max_size}"
            )

        # Set default angles if not provided
        if self.angles is None:
            self.angles = [2.0, -2.0]

        # Validate global settings
        if not 0 <= self.threshold <= 1:
            raise ValueError(
                f"threshold must be between 0 and 1, got: {self.threshold}"
            )
        if not self.angles:
            raise ValueError("angles cannot be empty")
        for angle in self.angles:
            if not -45 <= angle <= 45:
                raise ValueError(
                    f"angles must be between -45 and 45 degrees, got: {angle}"
                )

        # Ensure all strategy configurations are provided
        if self.general is None:
            raise ValueError("general strategy configuration is required")
        if self.thick_border is None:
            raise ValueError("thick_border strategy configuration is required")
        if self.thin_border is None:
            raise ValueError("thin_border strategy configuration is required")

        # Validate all strategy configurations
        for strategy_name, strategy_config in [
            ("general", self.general),
            ("thick_border", self.thick_border),
            ("thin_border", self.thin_border),
        ]:
            self._validate_strategy_config(strategy_name, strategy_config)

    def _validate_strategy_config(self, name: str, config: Dict[str, Any]) -> None:
        """Validate a strategy configuration dictionary."""
        if name == "general":
            # General strategy doesn't use border filtering
            required_keys = {"template_length",
                             "thickness", "min_contour_area"}
        else:
            # Border strategies require border_thickness
            required_keys = {
                "template_length",
                "thickness",
                "border_thickness",
                "min_contour_area",
            }

        if not all(key in config for key in required_keys):
            missing = required_keys - set(config.keys())
            raise ValueError(
                f"{name} strategy missing required keys: {missing}")

        if config["template_length"] <= 0:
            raise ValueError(f"{name}.template_length must be positive")
        if config["thickness"] < 7:
            raise ValueError(f"{name}.thickness must be at least 7")
        if config["min_contour_area"] <= 0:
            raise ValueError(f"{name}.min_contour_area must be positive")

        # Only validate border_thickness for border strategies
        if name != "general":
            if config["border_thickness"] < 0:
                raise ValueError(
                    f"{name}.border_thickness must be non-negative")


@dataclass
class GridRefinementClassifierConfig:
    """Classifier configuration for grid refinement."""

    model_path: str = ""
    features: List[str] = field(default_factory=list)
    threshold: float = 0.5


@dataclass
class GridRefinementConfig:
    """Configuration for grid refinement step."""

    classifier: GridRefinementClassifierConfig = field(
        default_factory=GridRefinementClassifierConfig
    )
    target_inclination_angles: Dict[str, float] = field(default_factory=dict)
    target_thickness: int = 22
    thickness_bias: float = 0.90

    def __post_init__(self) -> None:
        # Convert classifier dict to dataclass if needed
        if isinstance(self.classifier, dict):
            self.classifier = GridRefinementClassifierConfig(**self.classifier)
        if self.classifier is None:
            raise ValueError(
                "classifier configuration is required for grid refinement")
        if self.classifier.model_path and not os.path.isfile(
            self.classifier.model_path
        ):
            raise ValueError(
                f"classifier.model_path does not exist: {self.classifier.model_path}"
            )
        if not self.classifier.features:
            raise ValueError("classifier.features must not be empty")
        if not (0.0 <= self.classifier.threshold <= 1.0):
            raise ValueError("classifier.threshold must be between 0 and 1")
        if self.target_inclination_angles:
            required_keys = {"horizontal", "vertical", "tolerance"}
            missing = required_keys - \
                set(self.target_inclination_angles.keys())
            if missing:
                raise ValueError(
                    f"target_inclination_angles missing keys: {missing}")
            for k, v in self.target_inclination_angles.items():
                if not isinstance(v, (float, int)):
                    raise ValueError(
                        f"target_inclination_angles[{k}] must be a float")
        if not isinstance(self.target_thickness, int) or self.target_thickness <= 0:
            raise ValueError("target_thickness must be a positive integer")
        if not (0.0 <= self.thickness_bias <= 1.0):
            raise ValueError("thickness_bias must be between 0 and 1")


@dataclass
class InpaintingConfig:
    """Configuration for mask-based inpainting step."""

    model: str = "lama"  # Inpainting algorithm identifier
    mask_path: str = ""  # Directory containing mask images
    mask_suffix: str = "_mask"  # Suffix appended to filename to locate mask

    def __post_init__(self) -> None:
        """Validate inpainting configuration parameters."""
        valid_models = {"lama"}
        if self.model.lower() not in valid_models:
            raise ValueError(
                f"Invalid inpainting model: {self.model}. "
                f"Valid models: {', '.join(sorted(valid_models))}"
            )
        if self.mask_path and not os.path.isdir(self.mask_path):
            raise ValueError(f"mask_path does not exist: {self.mask_path}")


@dataclass
class StitchingConfig:
    """Configuration for whole slide stitching step."""
    output_filename: str = "stitched_slide.ome.tif"  # Name of generated OME-TIFF
    pattern: str = "TileScan_001_s{series:3}_ch{channel:2}.tiff"  # File pattern used by Ashlar
    overlap: float = 0.1  # Fractional tile overlap for registration
    pixel_size: float = 1.0  # Physical pixel size in microns
    width: int = 1  # Tile grid width
    height: int = 1  # Tile grid height
    layout: str = "raster"  # Acquisition layout
    direction: str = "horizontal"  # Raster direction

    def __post_init__(self) -> None:
        """Validate stitching configuration parameters."""
        if not self.output_filename:
            raise ValueError("output_filename must be specified")
        if not self.pattern:
            raise ValueError("pattern must be specified")
        if not 0 <= self.overlap < 1:
            raise ValueError("overlap must be between 0 and 1")
        if self.pixel_size <= 0:
            raise ValueError("pixel_size must be positive")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive integers")


@dataclass
class DebugConfig:
    """Debug configuration for controlling artifact generation."""

    relative_path: Optional[str] = None  # Location inside the run's output directory
    saved_artifact_type: str = "image"  # "image", "data", or "both"
    save_composite_img: bool = False  # Generate composite visualization images
    save_aggregated_data: bool = False  # Persist aggregated results
    input_result_file_name: Optional[str] = None
    result_file_name: str = field(default="aggregated_data.json", init=False)
    path: str = field(init=False, default="")
    artifact_sink: str = "local"  # "local" or "memory"

    def __post_init__(self) -> None:  # pragma: no cover - simple validation
        valid_types = {"image", "data", "both"}
        if self.saved_artifact_type not in valid_types:
            raise ValueError(
                "saved_artifact_type must be one of 'image', 'data', or 'both'"
            )
        valid_sinks = {"local", "memory"}
        if self.artifact_sink not in valid_sinks:
            raise ValueError(
                f"artifact_sink must be one of {valid_sinks}, got: {self.artifact_sink}"
            )
        # The actual path is resolved by AppConfigManager
        self.path = self.relative_path or ""


@dataclass
class LogConfig:
    """Configuration for application logging system.

    Supports file-based and stream-based logging. When ``stream`` is
    provided it takes precedence over writing to a file, enabling use in
    environments without filesystem access.
    """

    log_to_file: bool = False
    log_to_console: bool = True
    log_file_name: str = "app.log"
    log_level: str = "INFO"
    stream: Optional[IO[str]] = field(default=None, repr=False, compare=False)
    relative_path: Optional[str] = None
    path: str = field(init=False, default="")

    def __post_init__(self) -> None:  # pragma: no cover - simple validation
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(
                f"Invalid log level: {self.log_level}. "
                f"Valid levels: {', '.join(sorted(valid_levels))}"
            )
        self.path = self.relative_path or ""
