from abc import ABC, abstractmethod
import numpy as np
from typing import Optional


class BaseDrawer(ABC):
    """Base class for all step-specific debug visualization drawers."""

    def __init__(self, enabled: bool = True) -> None:
        """
        Initialize base drawer.
        
        Args:
            enabled: Whether visualization is enabled
        """
        self.enabled = enabled

    @abstractmethod
    def draw(self) -> Optional[np.ndarray]:
        """
        Create the debug visualization.
        
        Returns:
            Debug visualization image as numpy array, or None if disabled
        """
        pass

    def is_enabled(self) -> bool:
        """Check if the drawer is enabled."""
        return self.enabled
