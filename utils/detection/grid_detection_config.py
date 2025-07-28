from utils.config_manager import ConfigManager

class GridDetectionConfig(ConfigManager):
    """
    Provides typed accessors for grid/line detection configuration parameters.

    Inherits from ConfigManager and exposes properties for all relevant config options,
    including pipeline parameters, logging, and debug settings.

    Properties
    ----------
    angle_deg : float
        Rotation angle in degrees.
    margin : int
        Margin for edge detection.
    percentile_thresh : int
        Percentile threshold for template matching.
    horizontal_area_threshold : int
        Minimum area for horizontal lines.
    vertical_area_threshold : int
        Minimum area for vertical lines.
    line_length : int
        Length of the line template.
    line_thickness : int
        Thickness of the line template.
    log_to_file : bool
        Enable logging to file.
    log_to_console : bool
        Enable logging to console.
    log_file_name : str
        Log file name.
    debug_enabled : bool
        Enable debug features.
    debug_visualization : bool
        Enable debug visualization.
    debug_logging : bool
        Enable debug logging.
    debug_output_dir : str
        Output directory for debug products.
    """

    @property
    def angle_deg(self) -> float:
        """Rotation angle in degrees."""
        return self.get("angle_deg")

    @property
    def margin(self) -> int:
        """Margin for edge detection."""
        return self.get("margin")

    @property
    def percentile_thresh(self) -> int:
        """Percentile threshold for template matching."""
        return self.get("percentile_thresh")

    @property
    def horizontal_area_threshold(self) -> int:
        """Minimum area for horizontal lines."""
        return self.get("horizontal_area_threshold")

    @property
    def vertical_area_threshold(self) -> int:
        """Minimum area for vertical lines."""
        return self.get("vertical_area_threshold")

    @property
    def line_length(self) -> int:
        """Length of the line template."""
        return self.get("line_length")

    @property
    def line_thickness(self) -> int:
        """Thickness of the line template."""
        return self.get("line_thickness")

    # Logging options (from "logging" group)
    @property
    def log_to_file(self) -> bool:
        """Enable logging to file."""
        return self.get("logging", {}).get("log_to_file", False)

    @property
    def log_to_console(self) -> bool:
        """Enable logging to console."""
        return self.get("logging", {}).get("log_to_console", False)

    @property
    def log_file_name(self) -> str:
        """Log file name."""
        return self.get("logging", {}).get("log_file_name", "detection.log")

    # Debug options (from "debug" group)
    @property
    def debug_enabled(self) -> bool:
        """Enable debug features."""
        return self.get("debug", {}).get("enabled", False)

    @property
    def debug_visualization(self) -> bool:
        """Enable debug visualization."""
        debug_cfg = self.get("debug", {})
        return debug_cfg.get("visualization", False) if "visualization" in debug_cfg and self.debug_enabled else False

    @property
    def debug_logging(self) -> bool:
        """Enable debug logging."""
        debug_cfg = self.get("debug", {})
        return debug_cfg.get("logging", False) if "logging" in debug_cfg and self.debug_enabled else False

    @property
    def debug_output_dir(self) -> str:
        """Output directory for debug products."""
        return self.get("debug", {}).get("output_dir", "debug_output")