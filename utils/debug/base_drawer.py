from abc import ABC, abstractmethod
import os
from typing import Optional


class BaseDrawer(ABC):
    """Base class for all step-specific debug visualization drawers."""

    def __init__(self, enabled: bool = True, output_dir: Optional[str] = None) -> None:
        """
        Initialize base drawer.
        
        Args:
            enabled: Whether visualization is enabled
            output_dir: Directory to save debug images
        """
        self.enabled = enabled
        self.output_dir = output_dir

    @abstractmethod
    def save(self, filename: str) -> None:
        """
        Save the debug visualization with the given filename.
        
        Args:
            filename: Name of the output file
        """
        pass

    def is_enabled(self) -> bool:
        """Check if the drawer is enabled."""
        return self.enabled

    def _get_output_path(self, filename: str) -> str:
        """
        Get the full output path for a given filename.
        
        Args:
            filename: Base filename
            
        Returns:
            Full path including output directory
        """
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            return os.path.join(self.output_dir, filename)
        return filename
