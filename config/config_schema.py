from dataclasses import dataclass
from typing import Optional, List, Dict, Any
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
            "otsu", "triangle", "li", "yen", "isodata", "minimum",
            "combined_differential", "adaptive_gaussian", "adaptive_mean"
        }
        if self.threshold_method.lower() not in valid_methods:
            raise ValueError(f"Invalid threshold method: {self.threshold_method}. "
                             f"Valid methods: {', '.join(sorted(valid_methods))}")


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
                f"cache_max_size must be positive, got: {self.cache_max_size}")

        # Set default angles if not provided
        if self.angles is None:
            self.angles = [2.0, -2.0]

        # Validate global settings
        if not 0 <= self.threshold <= 1:
            raise ValueError(
                f"threshold must be between 0 and 1, got: {self.threshold}")
        if not self.angles:
            raise ValueError("angles cannot be empty")
        for angle in self.angles:
            if not -45 <= angle <= 45:
                raise ValueError(
                    f"angles must be between -45 and 45 degrees, got: {angle}")

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
            ("thin_border", self.thin_border)
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
class GridRefinementConfig:
    """Configuration for grid refinement step."""

    analyze_thick_border: bool = True
    analyze_thin_border: bool = True

    def __post_init__(self) -> None:
        """Validate boolean flags."""
        for field in ("analyze_thick_border", "analyze_thin_border"):
            value = getattr(self, field)
            if not isinstance(value, bool):
                raise ValueError(f"{field} must be a boolean, got: {value}")


@dataclass
class DebugConfig:
    """
    Configuration for debugging and visualization output.

    Controls the generation of debug artifacts including intermediate
    images, composite visualizations, and detailed processing logs
    for development and troubleshooting purposes.
    """
    output_dir: str = "debug_output"  # Directory for debug artifacts
    save_composite: bool = False  # Generate composite visualization images
    save_results: bool = False  # Save numeric results to a file
    result_file_name: str = "results.csv"  # Filename for aggregated results


@dataclass
class LogConfig:
    """
    Configuration for application logging system.

    Defines log output destinations, verbosity levels, and file naming
    conventions. Supports both console and file output with configurable
    log levels for different deployment scenarios.
    """
    log_to_file: bool = False  # Enable file-based logging
    log_to_console: bool = True  # Enable console logging output
    log_file_name: str = "app.log"  # Log file name
    log_level: str = "INFO"  # Minimum log level to capture
    output_dir: str = "logs"  # Directory for log files

    def __post_init__(self) -> None:
        """
        Validate logging configuration parameters.

        Raises:
            ValueError: If log_level is not a standard logging level
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.log_level}. "
                             f"Valid levels: {', '.join(sorted(valid_levels))}")
