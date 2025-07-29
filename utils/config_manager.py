import json
import os
from typing import Any, Dict
from utils.logger import Logger

class ConfigManager:
    """
    ConfigManager

    Loads, saves, and manages configuration parameters for the grid/line detection pipeline.
    Provides centralized access to config values, logging setup, and debug/visualization options.

    Parameters
    ----------
    config_path : str
        Path to the JSON configuration file.

    Attributes
    ----------
    path : str
        Path to the loaded configuration file.
    _config : dict
        Dictionary containing all configuration parameters.
    logger : Logger
        Logger instance, set up according to config.

    Methods
    -------
    get(key: str, default: Any = None) -> Any
        Get a config value by key.
    set(key: str, value: Any) -> None
        Set a config value.
    save() -> None
        Save the current config to file.
    setup_debugging() -> None
        Set up debugging and visualization options from config.
    """

    path: str
    _config: Dict[str, Any]

    def __init__(self, config_path: str) -> None:
        self.path = config_path  # Store the config file path
        self._config = self._load_config(config_path)
        self.setup_debugging()

    def _load_config(self, path: str) -> Dict[str, Any]:
        with open(path, "r") as f:
            return json.load(f)

    def save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    def setup_debugging(self) -> None:
        if self.debug_visualization:
            os.makedirs(self.debug_output_dir, exist_ok=True)

        self.logger = Logger.get_instance(
            log_to_file=self.log_to_file,
            log_to_console=self.log_to_console,
            log_file_name=self.log_file_name,
            log_level=self.log_level,
            output_dir=self.debug_output_dir,
            disable_logging=not self.debug_logging
        )

    @property
    def config(self) -> Dict[str, Any]:
        """
        Returns the loaded configuration dictionary.
        """
        return self._config

    @property
    def debug_output_dir(self) -> str:
        """
        Returns the output directory for debug products, as set in the config file.
        """
        return self._config.get("debug", {}).get("output_dir", "debug_output")

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

    # Log options (from "logging" group)
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
        """File name for logging."""
        return self.get("logging", {}).get("log_file_name", "")

    @property
    def log_level(self) -> str:
        """Logging level."""
        return self.get("logging", {}).get("log_level", "INFO")