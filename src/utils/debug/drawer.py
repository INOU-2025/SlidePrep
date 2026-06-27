"""Abstract base class for step-specific debug visualisation."""

from abc import ABC, abstractmethod
import numpy as np
from typing import Optional, Any


class Drawer(ABC):
    """Base class for all step-specific debug visualization drawers."""

    @abstractmethod
    def draw(self, image: np.ndarray, results: Any = None, metadata: Any = None) -> Optional[np.ndarray]:
        """Draw visualizations onto image; return the result, or None if nothing to draw."""
        pass
