import json
from typing import Any, Dict
from abc import ABC, abstractmethod

class ConfigManager(ABC):
    
    def __init__(self, config_path: str):
        self._path = config_path
        self._config = self._load_config(config_path)
        self._extract_config_values()

    def _load_config(self, path: str) -> Dict[str, Any]:
        with open(path, "r") as f:
            return json.load(f)

    def save(self) -> None:
        with open(self._path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    @abstractmethod
    def _extract_config_values(self) -> None:
        pass

    