from dataclasses import dataclass

@dataclass
class GeneralConfig:
    """General configuration properties that apply to all scripts."""
    input_path: str = ""
    output_path: str = "output"
    suffix_filter: str = ""  # Only process files with this suffix (e.g., '_ch00', '_processed')

@dataclass
class BinarizationConfig:
    threshold_method: str

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

@dataclass
class DebugConfig:
    """Configuration for debugging and visualization."""
    enabled: bool = False
    visualization: bool = False
    logging: bool = True
    output_dir: str = "debug"

@dataclass
class LogConfig:
    """Configuration for logging."""
    log_to_file: bool = False
    log_to_console: bool = True
    log_file_name: str = ""
    log_level: str = "INFO"