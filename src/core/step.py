from abc import ABC, abstractmethod
from typing import Any, Optional
import numpy as np
from src.core.container import Container
from src.core.step_result import StepResult


class PipelineStep(ABC):
    """
    Base class for all pipeline processing steps.

    All pipeline steps are initialized with a configuration object specific to their functionality.
    This ensures consistent configuration management across the pipeline.
    """

    def __init__(self, name: str, config=None):
        """
        Initialize pipeline step.

        Args:
            name: Name of the pipeline step
            config: Configuration object specific to this step
        """
        self.name = name
        self.config = config
        self.container: Optional[Container] = None

    @abstractmethod
    def run(self, data: Any) -> StepResult:
        """
        Process input data and return output data.

        Args:
            data: Input data to process

        Returns:
            StepResult: Processed result containing output data and optional metadata.
        """
        pass

    def log(self, message: str) -> None:
        logger = self.logger
        if logger:
            logger.info(f"[{self.name}] {message}")
        else:
            print(f"[{self.name}] {message}")

    def debug(self, message: str) -> None:
        logger = self.logger
        if logger:
            logger.debug(f"[{self.name}] {message}")
        else:
            print(f"[{self.name}] DEBUG: {message}")

    def warning(self, message: str) -> None:
        logger = self.logger
        if logger:
            logger.warning(f"[{self.name}] {message}")
        else:
            print(f"[{self.name}] WARNING: {message}")

    def error(self, message: str) -> None:
        logger = self.logger
        if logger:
            logger.error(f"[{self.name}] {message}")
        else:
            print(f"[{self.name}] ERROR: {message}")

    def critical(self, message: str) -> None:
        logger = self.logger
        if logger:
            logger.critical(f"[{self.name}] {message}")
        else:
            print(f"[{self.name}] CRITICAL: {message}")

    @property
    def logger(self):
        if self.container:
            try:
                return self.container.resolve("logger")
            except KeyError:
                return None
        return None

    @property
    def debugger(self):
        if self.container:
            try:
                return self.container.resolve("debugger")
            except KeyError:
                return None
        return None

    @property
    def current_image_path(self) -> Optional[str]:
        """Path of the image currently being processed in the pipeline."""
        if self.container:
            try:
                context = self.container.resolve("pipeline_context")
                return context.input_image_path
            except KeyError:
                return None
        return None

    def _validate_image_input(self, data: Any) -> None:
        """
        Validate that input data is a well-formed image.

        All validation errors use the consistent message: "Input image must exist and must be a well-formed image"

        Args:
            data: Input data to validate

        Raises:
            ValueError: if data is None or zero-size
            TypeError: if data is not an ndarray
        """
        if data is None:
            raise ValueError(
                "Input image must exist and must be a well-formed image")

        if not isinstance(data, np.ndarray):
            raise TypeError(
                "Input image must exist and must be a well-formed image")

        if data.size == 0:
            raise ValueError(
                "Input image must exist and must be a well-formed image")
