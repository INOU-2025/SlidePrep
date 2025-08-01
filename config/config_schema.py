from dataclasses import dataclass

@dataclass
class BinarizationConfig:
    """
    Configuration for the Combined Differential binarization method.
    This is the production-ready method optimized for thick grid line detection.
    """
    threshold_method: str = "combined_differential"  # Fixed: only combined_differential supported

@dataclass
class GridDetectionConfig:
    angle_deg: float
    margin: int
    percentile_thresh: int
    horizontal_area_threshold: int
    vertical_area_threshold: int
    line_length: int
    line_thickness: int
    length_threshold_factor: float = 0.55  # Factor for minimum line length (relative to image dimension)

@dataclass
class DebugConfig:
    enabled: bool = False
    visualization: bool = False
    logging: bool = True
    output_dir: str = "debug"

@dataclass
class LogConfig:
    log_to_file: bool = True
    log_to_console: bool = True
    log_file_name: str = ""
    log_level: str = "DEBUG"
    output_dir: str = ""