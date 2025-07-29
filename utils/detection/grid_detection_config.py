from utils.config_manager import ConfigManager
import os

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
        return self.get("angle_deg", 0.0)

    @property
    def margin(self) -> int:
        """Margin for edge detection."""
        return self.get("margin", 0)

    @property
    def percentile_thresh(self) -> int:
        """Percentile threshold for template matching."""
        return self.get("percentile_thresh", 0)

    @property
    def horizontal_area_threshold(self) -> int:
        """Minimum area for horizontal lines."""
        return self.get("horizontal_area_threshold", 0)

    @property
    def vertical_area_threshold(self) -> int:
        """Minimum area for vertical lines."""
        return self.get("vertical_area_threshold", 0)

    @property
    def line_length(self) -> int:
        """Length of the line template."""
        return self.get("line_length", 0)

    @property
    def line_thickness(self) -> int:
        """Thickness of the line template."""
        return self.get("line_thickness", 0)