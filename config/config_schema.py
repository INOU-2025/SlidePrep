from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class GeneralConfig:
    """General configuration properties that apply to all scripts."""
    input_path: str = ""
    output_path: str = "output"
    suffix_filter: str = ""
    output_suffix: str = ""
    log: bool = True
    debug: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.input_path and not os.path.exists(self.input_path):
            raise ValueError(f"Input path does not exist: {self.input_path}")

@dataclass
class BinarizationConfig:
    """Configuration for binarization step."""
    threshold_method: str = "combined_differential"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        valid_methods = {
            "otsu", "triangle", "li", "yen", "isodata", "minimum", 
            "combined_differential", "adaptive_gaussian", "adaptive_mean"
        }
        if self.threshold_method.lower() not in valid_methods:
            raise ValueError(f"Invalid threshold method: {self.threshold_method}. "
                           f"Valid methods: {', '.join(sorted(valid_methods))}")

@dataclass
class GridDetectionConfig:
    """Configuration for grid detection step."""
    angle_deg: float
    margin: int
    percentile_thresh: int
    horizontal_area_threshold: int
    vertical_area_threshold: int
    line_length: int
    line_thickness: int
    length_threshold_factor: float
    
    def __post_init__(self):
        """Validate configuration after initialization."""
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
    """Configuration for debugging and visualization."""
    output_dir: str = "debug_output"
    save_composite: bool = False

@dataclass
class LogConfig:
    """Configuration for logging."""
    log_to_file: bool = False
    log_to_console: bool = True
    log_file_name: str = "app.log"
    log_level: str = "INFO"
    output_dir: str = "logs"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.log_level}. "
                           f"Valid levels: {', '.join(sorted(valid_levels))}")