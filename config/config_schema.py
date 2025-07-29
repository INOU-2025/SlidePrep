from dataclasses import dataclass

@dataclass
class GridDetectionConfig:
    angle_deg: float
    margin: int
    percentile_thresh: int
    horizontal_area_threshold: int
    vertical_area_threshold: int
    line_length: int
    line_thickness: int

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