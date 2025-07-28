from utils.config_manager import ConfigManager

class GridDetectionConfig(ConfigManager):
    @property
    def angle_deg(self) -> float:
        return self.get("angle_deg")

    @property
    def margin(self) -> int:
        return self.get("margin")

    @property
    def percentile_thresh(self) -> int:
        return self.get("percentile_thresh")

    @property
    def horizontal_area_threshold(self) -> int:
        return self.get("horizontal_area_threshold")

    @property
    def vertical_area_threshold(self) -> int:
        return self.get("vertical_area_threshold")

    @property
    def line_length(self) -> int:
        return self.get("line_length")

    @property
    def line_thickness(self) -> int:
        return self.get("line_thickness")

    # Logging options (from "logging" group)
    @property
    def log_to_file(self) -> bool:
        return self.get("logging", {}).get("log_to_file", False)

    @property
    def log_to_console(self) -> bool:
        return self.get("logging", {}).get("log_to_console", False)

    @property
    def log_file_name(self) -> str:
        return self.get("logging", {}).get("log_file_name", "detection.log")

    # Debug options (from "debug" group)
    @property
    def debug_enabled(self) -> bool:
        return self.get("debug", {}).get("enabled", False)

    @property
    def debug_visualization(self) -> bool:
        debug_cfg = self.get("debug", {})
        return debug_cfg.get("visualization", False) if "visualization" in debug_cfg and self.debug_enabled else False

    @property
    def debug_logging(self) -> bool:
        debug_cfg = self.get("debug", {})
        return debug_cfg.get("logging", False) if "logging" in debug_cfg and self.debug_enabled else False

    @property
    def debug_output_dir(self) -> str:
        return self.get("debug", {}).get("output_dir", "debug_output")