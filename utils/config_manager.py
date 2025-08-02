import json
from typing import Any, Dict
from abc import ABC, abstractmethod

class ConfigManager(ABC):
    """Abstract base class for configuration management."""
    
    def __init__(self, config_path: str):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self._path = config_path
        self._config = self._load_config(config_path)
        self._extract_config_values()

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        with open(path, "r") as f:
            return json.load(f)

    def save(self) -> None:
        """Save current configuration back to file."""
        with open(self._path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by key.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self._config[key] = value

    @abstractmethod
    def _extract_config_values(self) -> None:
        """Extract and validate configuration values. Must be implemented by subclasses."""
        pass

    