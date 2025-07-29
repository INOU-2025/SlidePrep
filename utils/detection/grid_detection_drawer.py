import cv2
import numpy as np
import os
from typing import Optional


class GridDetectionDrawer:
    """
    Handles drawing and saving overlays for grid/line detection visualization.
    """

    def __init__(self, overlay: np.ndarray, enabled: bool = True, output_dir: Optional[str] = None) -> None:
        """
        Parameters
        ----------
        overlay : np.ndarray
            The image overlay to draw on.
        enabled : bool, optional
            Whether visualization is enabled (default: True).
        output_dir : Optional[str], optional
            Directory to save overlay images (default: None — use full path in `save()`).
        """
        self.overlay = overlay
        self.enabled = enabled
        self.output_dir = output_dir

    def draw_box(
        self, 
        box: np.ndarray, 
        color: tuple[int, int, int] = (0, 255, 255), 
        thickness: int = 1
    ) -> None:
        if self.enabled:
            cv2.drawContours(self.overlay, [box], 0, color, thickness)

    def draw_contour(
        self, 
        contour: np.ndarray, 
        accepted: bool = False, 
        maybe: bool = False
    ) -> None:
        if not self.enabled:
            return
        if accepted:
            color = (0, 0, 255)      # Red
        elif maybe:
            color = (0, 255, 0)      # Green
        else:
            color = (255, 0, 0)      # Blue
        cv2.drawContours(self.overlay, [contour], 0, color, 2)

    def save(self, filename: str) -> None:
        """
        Save the overlay image. If output_dir is set, filename is relative to it.
        Otherwise, filename is treated as full path.
        """
        if not self.enabled:
            return

        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            out_path = os.path.join(self.output_dir, filename)
        else:
            out_path = filename

        cv2.imwrite(out_path, self.overlay)
