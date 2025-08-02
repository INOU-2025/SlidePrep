from dataclasses import dataclass
from typing import Optional
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
    Configuration for grid pattern detection in binarized images.
    
    Defines parameters for template matching, contour analysis, and
    validation criteria used to identify grid lines. Controls the
    sensitivity and accuracy of the detection algorithm through
    geometric constraints and quality thresholds.
    """
    angle_deg: float  # Maximum rotation angle tolerance for grid lines
    margin: int  # Border margin for edge detection analysis
    percentile_thresh: int  # Template matching threshold percentile
    horizontal_area_threshold: int  # Minimum area for horizontal line candidates  
    vertical_area_threshold: int  # Minimum area for vertical line candidates
    line_length: int  # Template line length in pixels
    line_thickness: int  # Template line thickness in pixels
    length_threshold_factor: float  # Length factor for override decisions
    
    def __post_init__(self) -> None:
        """
        Validate grid detection parameters for reasonable ranges.
        
        Raises:
            ValueError: If any parameter is outside acceptable bounds
        """
        if not 0 <= self.angle_deg <= 45:
            raise ValueError(f"angle_deg must be between 0 and 45, got: {self.angle_deg}")
        if not 0 < self.percentile_thresh <= 100:
            raise ValueError(f"percentile_thresh must be between 1 and 100, got: {self.percentile_thresh}")
        if not 0 < self.length_threshold_factor <= 1:
            raise ValueError(f"length_threshold_factor must be between 0 and 1, got: {self.length_threshold_factor}")
        if self.line_thickness <= 0:
            raise ValueError(f"line_thickness must be positive, got: {self.line_thickness}")
        if self.line_length <= 0:
            raise ValueError(f"line_length must be positive, got: {self.line_length}")

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