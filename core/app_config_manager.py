from config.config_schema import GeneralConfig, GridDetectionConfig, BinarizationConfig, LogConfig, DebugConfig
from utils.config_manager import ConfigManager

class AppConfigManager(ConfigManager):

    def _extract_config_values(self):
        try:
            self.general_config = GeneralConfig(**self.get("general", {}))
            self.binarization_config = BinarizationConfig(**self.get("binarization", {}))
            self.grid_detection_config = GridDetectionConfig(**self.get("grid_detection", {}))
            self.logging_config = LogConfig(**self.get("logging", {}))
            self.debug_config = DebugConfig(**self.get("debug", {}))
        except TypeError as e:
            raise ValueError("Error extracting config values. Malformed or incomplete configuration") from e

    @property
    def logger_active(self) -> bool:
        return self.debug_config.enabled and self.debug_config.logging

