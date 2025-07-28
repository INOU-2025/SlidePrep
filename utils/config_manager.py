import json
import logging

class ConfigManager:
    def __init__(self, config_path):
        self._config = self._load_config(config_path)
        self.setup_logging()

    def _load_config(self, path):
        with open(path, "r") as f:
            return json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value

    def setup_logging(self):
        handlers = []
        log_format = "%(asctime)s %(levelname)s %(message)s"
        if self.get("log_to_file", True):
            handlers.append(logging.FileHandler(self.get("log_file_name", "detection.log")))
        if self.get("log_to_console", True):
            handlers.append(logging.StreamHandler())
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=handlers
        )

    @property
    def config(self):
        return self._config