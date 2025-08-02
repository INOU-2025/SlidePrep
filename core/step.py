from abc import ABC, abstractmethod
from typing import Any
from core.container import Container


class PipelineStep(ABC):
    """Base class for all pipeline processing steps."""
    
    def __init__(self, name: str, **kwargs):
        """
        Initialize pipeline step.
        
        Args:
            name: Name of the pipeline step
            **kwargs: Additional arguments (unused but allows flexible inheritance)
        """
        self.name = name

    @abstractmethod
    def run(self, data: Any) -> Any:
        """
        Process input data and return output data.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed output data
        """
        pass

    def log(self, message: str) -> None:
        """
        Log an info message with step prefix.
        
        Args:
            message: Message to log
        """
        try:
            logger = Container.resolve("logger")
            logger.info(f"[{self.name}] {message}")
        except KeyError:
            print(f"[{self.name}] {message}")

    def debug(self, message: str) -> None:
        """
        Log a debug message with step prefix.
        
        Args:
            message: Message to log
        """
        try:
            logger = Container.resolve("logger")
            logger.debug(f"[{self.name}] {message}")
        except KeyError:
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