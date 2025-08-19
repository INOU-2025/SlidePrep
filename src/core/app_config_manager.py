import os
from pydantic import ValidationError

from config.config_schema import (
    GeneralConfig,
    TestConfig,
    BinarizationConfig,
    ImgConversionConfig,
    GridDetectionConfig,
    GridRefinementConfig,
    InpaintingConfig,
    StitchingConfig,
    LogConfig,
    DebugConfig,
)
from src.utils.config_manager import ConfigManager


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
            test_cfg = self.get("test")
            self.test_config = TestConfig(**test_cfg) if test_cfg else None

            img_conv_config = self.get("img_conversion")
            self.img_conversion_config = (
                ImgConversionConfig(**img_conv_config) if img_conv_config else None
            )

            bin_config = self.get("binarization")
            self.binarization_config = (
                BinarizationConfig(**bin_config) if bin_config else None
            )

            grid_config = self.get("grid_detection")
            self.grid_detection_config = (
                GridDetectionConfig(**grid_config) if grid_config else None
            )

            refine_config = self.get("grid_refinement")
            self.grid_refinement_config = (
                GridRefinementConfig(**refine_config) if refine_config else None
            )

            inpaint_config = self.get("inpainting")
            self.inpainting_config = (
                InpaintingConfig(**inpaint_config) if inpaint_config else None
            )

            stitch_config = self.get("stitching")
            self.stitching_config = (
                StitchingConfig(**stitch_config) if stitch_config else StitchingConfig()
            )

            self.log_config = LogConfig(**self.get("log", {}))
            self.debug_config = DebugConfig(**self.get("debug", {}))

            base_output = (
                self.test_config.output_path
                if self.test_config and self.test_config.output_path
                else self.general_config.output_path
            )
            self.log_config.path = (
                os.path.join(base_output, self.log_config.relative_path)
                if self.log_config.relative_path
                else base_output
            )
            self.debug_config.path = (
                os.path.join(base_output, self.debug_config.relative_path)
                if self.debug_config.relative_path
                else base_output
            )

        except ValidationError as e:
            raise ValueError(
                f"Error extracting config values. Malformed configuration: {e}"
            ) from e

    @property
    def logger_active(self) -> bool:
        """Check if logging is enabled in general configuration."""
        return self.general_config.log

    @property
    def debug_active(self) -> bool:
        """Check if debugging is enabled in general configuration."""
        return self.general_config.debug
