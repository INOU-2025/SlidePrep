from dataclasses import dataclass

@dataclass
class GeneralConfig:
    """General configuration properties that apply to all scripts."""
    input_path: str = ""
    output_path: str = "output"
    suffix_filter: str = ""
    output_suffix: str = ""
    log: bool = True
    debug: bool = False

@dataclass
class BinarizationConfig:
    """Configuration for binarization step."""
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
    output_dir: str = "debug"
    save_composite: bool = False

@dataclass
class LogConfig:
    """Configuration for logging."""
    log_to_file: bool = False
    log_to_console: bool = True
    log_file_name: str = ""
    log_level: str = "INFO"
    output_dir: str = "logs"