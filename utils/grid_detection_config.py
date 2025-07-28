from utils.config_manager import ConfigManager

class GridDetectionConfig(ConfigManager):
    @property
    def angle_deg(self):
        return self.get("angle_deg")

    @property
    def margin(self):
        return self.get("margin")

    @property
    def percentile_thresh(self):
        return self.get("percentile_thresh")

    @property
    def horizontal_area_threshold(self):
        return self.get("horizontal_area_threshold")

    @property
    def vertical_area_threshold(self):
        return self.get("vertical_area_threshold")

    @property
    def line_length(self):
        return self.get("line_length")

    @property
    def line_thickness(self):
        return self.get("line_thickness")

    @property
    def log_to_file(self):
        return self.get("log_to_file", True)

    @property
    def log_to_console(self):
        return self.get("log_to_console", True)

    @property
    def log_file_name(self):
        return self.get("log_file_name", "detection.log")