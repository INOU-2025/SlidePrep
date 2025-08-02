from typing import List, Optional
from config.config_schema import GeneralConfig, GridDetectionConfig, BinarizationConfig, LogConfig, DebugConfig
from utils.config_manager import ConfigManager


class AppConfigManager(ConfigManager):
    """Application-specific configuration manager with typed config sections."""

    def __init__(self, config_path: str):
        """
        Initialize application configuration manager.

        Args:
            config_path: Path to the configuration file
        """
        super().__init__(config_path)

    def _extract_config_values(self):
        """Extract and validate configuration values into typed objects with graceful handling."""
        try:
            self.general_config = GeneralConfig(**self.get("general", {}))

            bin_config = self.get("binarization")
            self.binarization_config = (
                BinarizationConfig(**bin_config) if bin_config else None
            )

            grid_config = self.get("grid_detection")
            self.grid_detection_config = (
                GridDetectionConfig(**grid_config) if grid_config else None
            )

            self.log_config = LogConfig(**self.get("log", {}))
            self.debug_config = DebugConfig(**self.get("debug", {}))

        except TypeError as e:
            raise ValueError(
                f"Error extracting config values. Malformed configuration: {e}") from e

    @property
    def logger_active(self) -> bool:
        """Check if logging is enabled in general configuration."""
        return self.general_config.log

    @property
    def debug_active(self) -> bool:
        """Check if debugging is enabled in general configuration."""
        return self.general_config.debug
