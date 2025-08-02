from abc import ABC, abstractmethod
import numpy as np
from typing import Optional, Any


class BaseDrawer(ABC):
    """Base class for all step-specific debug visualization drawers."""

    @abstractmethod
    def draw(self, image: np.ndarray, results: Any = None, metadata: Any = None) -> Optional[np.ndarray]:
        """
        Draw results/metadata on top of the given image.
        
        Args:
            image: Base image to draw on
            results: Processing results to visualize
            metadata: Additional metadata for visualization
            
        Returns:
            Image with drawn visualizations, or None if nothing to draw
        """
        pass

