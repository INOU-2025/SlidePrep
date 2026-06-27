import json
import yaml
import os
from typing import Any, Dict
from abc import ABC, abstractmethod


class ConfigManager(ABC):
    """Abstract base class for configuration management."""

    def __init__(self, config_path: str):
        self._path = config_path
        self._config = self._load_config(config_path)
        self._extract_config_values()

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load configuration from JSON or YAML file."""
        with open(path, "r") as f:
            if path.endswith(('.yaml', '.yml')):
                return yaml.safe_load(f)
            return json.load(f)

    def save(self) -> None:
        """Save current configuration back to file."""
        with open(self._path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Return config value for key, or default if not found."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set config value for key."""
        self._config[key] = value

    @abstractmethod
    def _extract_config_values(self) -> None:
        """Extract and validate configuration values. Must be implemented by subclasses."""
        pass
