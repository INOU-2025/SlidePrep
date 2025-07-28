import json
import logging
from typing import Any, Dict

class NoOpLogger:
    def info(self, *args, **kwargs) -> None: pass
    def error(self, *args, **kwargs) -> None: pass
    def exception(self, *args, **kwargs) -> None: pass

class ConfigManager:
    path: str
    _config: Dict[str, Any]
    visualization_enabled: bool

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
        logging_cfg: Dict[str, Any] = self.get("logging", {})
        log_to_file: bool = logging_cfg.get("log_to_file", False)
        log_file_name: str = logging_cfg.get("log_file_name", "")
        log_to_console: bool = logging_cfg.get("log_to_console", False)
        log_level_str: str = logging_cfg.get("log_level", "INFO")
        log_format: str = "%(asctime)s %(levelname)s %(message)s"

        log_level: int = getattr(logging, log_level_str.upper(), logging.INFO)

        if log_to_file and log_file_name:
            handlers.append(logging.FileHandler(log_file_name))
        if log_to_console:
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
        debug_cfg: Dict[str, Any] = self.get("debug", {})
        debug_enabled: bool = debug_cfg.get("enabled", False)
        debug_logging: bool = debug_cfg.get("logging", False) if "logging" in debug_cfg else False
        debug_visualization: bool = debug_cfg.get("visualization", False) if "visualization" in debug_cfg else False

        self.visualization_enabled = debug_enabled and debug_visualization

        if debug_enabled and debug_logging:
            self.setup_logging()
            self.logger = logging.getLogger()
        else:
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
                handler.close()
            logging.disable(logging.CRITICAL)
            self.logger = NoOpLogger()

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @property
    def debug_output_dir(self) -> str:
        return self._config.get("debug", {}).get("output_dir", "debug_output")