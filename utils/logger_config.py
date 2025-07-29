from dataclasses import dataclass

@dataclass
class LogConfig:
    log_to_file: bool = False
    log_to_console: bool = True
    log_file_name: str = ""
    log_level: str = "INFO"
    output_dir: str = "debug_output"