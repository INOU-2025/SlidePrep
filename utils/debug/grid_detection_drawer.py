import cv2
import numpy as np
from typing import Optional

from .base_drawer import BaseDrawer


class GridDetectionDrawer(BaseDrawer):
    """
    Specialized drawer for grid detection step debugging.
    Draws contours, bounding boxes, and detection results on the original image.
    """

    def __init__(self, overlay: np.ndarray, enabled: bool = True, output_dir: Optional[str] = None) -> None:
        """
        Parameters
        ----------
        overlay : np.ndarray
            The image overlay to draw on (should be BGR format).
        enabled : bool, optional
            Whether visualization is enabled (default: True).
        output_dir : Optional[str], optional
            Directory to save debug images (default: None).
        """
        super().__init__(enabled, output_dir)
        self.overlay = overlay.copy() if enabled else None

    def draw_box(
        self, 
        box: np.ndarray, 
        color: tuple[int, int, int] = (255, 0, 0), # Blue
        thickness: int = 1
    ) -> None:
        """Draw a bounding box on the overlay."""
        if self.enabled and self.overlay is not None:
            cv2.drawContours(self.overlay, [box], 0, color, thickness)

    def draw_contour(
        self, 
        contour: np.ndarray, 
        accepted: bool = False, 
        maybe: bool = False
    ) -> None:
        """Draw a contour with color coding based on acceptance status."""
        if not self.enabled or self.overlay is None:
            return
            
        if accepted:
            color = (0, 255, 0)  # Green for accepted
        elif maybe:
            color = (0, 255, 255)  # Yellow for maybe
        else:
            color = (0, 0, 255)  # Red for rejected
            
        cv2.drawContours(self.overlay, [contour], 0, color, 2)

    def save(self, filename: str) -> None:
        """Save the overlay image with all drawn elements."""
        if not self.enabled or self.overlay is None:
            return

        try:
            output_path = self._get_output_path(filename)
            cv2.imwrite(output_path, self.overlay)
        except Exception as e:
            # Silently fail to avoid disrupting the main pipeline
            pass
