import json
import logging

class NoOpLogger:
    def info(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def exception(self, *args, **kwargs): pass

class ConfigManager:
    def __init__(self, config_path):
        self.path = config_path  # Store the config file path
        self._config = self._load_config(config_path)
        self.setup_debugging()

    def _load_config(self, path):
        with open(path, "r") as f:
            return json.load(f)

    def save(self):
        """
        Save the current configuration to the file specified by self.path.

        Raises:
            AttributeError: If self.path is not set.
            IOError: If the file cannot be written.
        """
        with open(self.path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value

    def setup_logging(self):
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        handlers = []
        logging_cfg = self.get("logging", {})
        log_to_file = logging_cfg.get("log_to_file", False)
        log_file_name = logging_cfg.get("log_file_name", "")
        log_to_console = logging_cfg.get("log_to_console", False)
        log_level_str = logging_cfg.get("log_level", "INFO")
        log_format = "%(asctime)s %(levelname)s %(message)s"

        # Convert log level string to logging constant
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)

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

    def setup_debugging(self):
        debug_cfg = self.get("debug", {})
        debug_enabled = debug_cfg.get("enabled", False)
        debug_logging = debug_cfg.get("logging", False) if "logging" in debug_cfg else False
        debug_visualization = debug_cfg.get("visualization", False) if "visualization" in debug_cfg else False
        debug_output_dir = debug_cfg.get("output_dir", "debug_output") if "output_dir" in debug_cfg else "debug_output"

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
    def config(self):
        return self._config

    @property
    def debug_output_dir(self):
        return self._config.get("debug", {}).get("output_dir", "debug_output")