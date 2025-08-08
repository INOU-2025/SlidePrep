from abc import ABC, abstractmethod
from typing import Any


class ResultWriter(ABC):
    """Base class for all step-specific debug result writers."""

    @abstractmethod
    def write(self, path: str, results: Any, metadata: Any = None) -> None:
        """Write results to the given output path.

        Args:
            path: Destination file path.
            results: Data produced by the pipeline step.
            metadata: Optional additional information about the results.
        """
        raise NotImplementedError