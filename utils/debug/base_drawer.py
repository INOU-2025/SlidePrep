from abc import ABC, abstractmethod
import os
from typing import Optional


class BaseDrawer(ABC):
    """
    Base class for all step-specific drawers.
    Each step can have its own specialized drawer implementation.
    """

    def __init__(self, enabled: bool = True, output_dir: Optional[str] = None) -> None:
        """
        Parameters
        ----------
        enabled : bool, optional
            Whether visualization is enabled (default: True).
        output_dir : Optional[str], optional
            Directory to save debug images (default: None).
        """
        self.enabled = enabled
        self.output_dir = output_dir

    @abstractmethod
    def save(self, filename: str) -> None:
        """Save the debug visualization with the given filename."""
        pass

    def is_enabled(self) -> bool:
        """Check if the drawer is enabled."""
        return self.enabled

    def _get_output_path(self, filename: str) -> str:
        """Get the full output path for a given filename."""
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            return os.path.join(self.output_dir, filename)
        return filename
