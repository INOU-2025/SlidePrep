from abc import ABC, abstractmethod
from typing import Any, Optional
from core.container import Container


class PipelineStep(ABC):
    def __init__(self, name: str, **kwargs):
        self.name = name

    @abstractmethod
    def run(self, data: Any) -> Any:
        """Process input data and return output data."""
        pass

    def log(self, message: str) -> None:
        """Log an info message with step prefix."""
        try:
            logger = Container.resolve("logger")
            logger.info(f"[{self.name}] {message}")
        except KeyError:
            # Fallback if logger not available
            print(f"[{self.name}] {message}")

    def debug(self, message: str) -> None:
        """Log a debug message with step prefix."""
        try:
            logger = Container.resolve("logger")
            logger.debug(f"[{self.name}] {message}")
        except KeyError:
            # Fallback if logger not available
            print(f"[{self.name}] DEBUG: {message}")

    @property
    def logger(self):
        """Get the logger from the container."""
        try:
            return Container.resolve("logger")
        except KeyError:
            return None

    @property
    def debugger(self):
        """Get the debugger from the container."""
        try:
            return Container.resolve("debugger")
        except KeyError:
            return None

    @property
    def config_manager(self):
        """Get the config manager from the container."""
        try:
            return Container.resolve("config")
        except KeyError:
            return None