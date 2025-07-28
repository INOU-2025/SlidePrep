import json

class ConfigManager:
    def __init__(self, path):
        self.path = path
        self._config = self._load()

    def _load(self):
        with open(self.path, "r") as f:
            return json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value

    @property
    def config(self):
        return self._config