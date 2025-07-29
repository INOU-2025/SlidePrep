import json
import logging
import os
from typing import Any, Dict

class NoOpLogger:
    def info(self, *args, **kwargs) -> None: pass
    def error(self, *args, **kwargs) -> None: pass
    def exception(self, *args, **kwargs) -> None: pass
    def debug(self, *args, **kwargs) -> None: pass

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
    logger : logging.Logger or NoOpLogger
        Logger instance, set up according to config.

    Methods
    -------
    get(key: str, default: Any = None) -> Any
        Get a config value by key.
    set(key: str, value: Any) -> None
        Set a config value.
    save() -> None
        Save the current config to file.
    setup_logging() -> None
        Set up logging handlers and level from config.
    setup_debugging() -> None
        Set up debugging and visualization options from config.

    Config File Structure
    --------------------
    The config file should be a JSON file with keys such as:

    {
      "logging": {
        "log_to_file": true,
        "log_to_console": false,
        "log_file_name": "detection.log",
        "log_level": "INFO"  # Valid values: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"
      },
      "debug": {
        "enabled": true,
        "visualization": true,
        "logging": false,
        "output_dir": "debug_output"
      }
      // ... other pipeline parameters ...
    }

    Notes
    -----
    - Use the 'log_level' key to control which log messages are shown.
    - Use 'visualization' and 'enabled' in the 'debug' section to control debug visualization.
    - Use 'output_dir' in the 'debug' section to set the output directory for results.
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

    def setup_logging(self) -> None:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        handlers: list[Any] = []
        log_format: str = "%(asctime)s %(levelname)s %(message)s"
        log_level: int = getattr(logging, self.log_level.upper(), logging.INFO)

        if self.log_to_file and self.log_file_name:
            os.makedirs(self.debug_output_dir, exist_ok=True)
            handlers.append(logging.FileHandler(os.path.join(self.debug_output_dir, self.log_file_name)))
        if self.log_to_console:
            handlers.append(logging.StreamHandler())

        if handlers:
            logging.basicConfig(
                level=log_level,
                format=log_format,
                handlers=handlers
            )
        else:
            logging.disable(logging.CRITICAL)

    def setup_debugging(self) -> None:

        if self.debug_visualization:
            os.makedirs(self.debug_output_dir, exist_ok=True)

        if self.debug_logging:
            self.setup_logging()
            self.logger: logging.Logger = logging.getLogger()
        else:
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
                handler.close()
            logging.disable(logging.CRITICAL)
            self.logger: NoOpLogger = NoOpLogger()

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