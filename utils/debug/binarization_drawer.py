import cv2
import numpy as np
from typing import Optional

from .base_drawer import BaseDrawer


class BinarizationDrawer(BaseDrawer):
    """
    Specialized drawer for binarization step debugging.
    Creates side-by-side comparisons of original and binarized images.
    """

    def __init__(self, original_image: np.ndarray, enabled: bool = True, output_dir: Optional[str] = None) -> None:
        """
        Parameters
        ----------
        original_image : np.ndarray
            The original grayscale image for comparison.
        enabled : bool, optional
            Whether visualization is enabled (default: True).
        output_dir : Optional[str], optional
            Directory to save debug images (default: None).
        """
        super().__init__(enabled, output_dir)
        self.original_image = original_image
        self.binarized_image = None
        self.method_info = ""

    def set_binarized_image(self, binarized_image: np.ndarray, method_info: str = "") -> None:
        """Set the binarized image result and method information."""
        if self.enabled:
            self.binarized_image = binarized_image
            self.method_info = method_info

    def save(self, filename: str) -> None:
        """Save side-by-side comparison of original and binarized images."""
        if not self.enabled or self.binarized_image is None:
            return

        try:
            # Create side-by-side comparison
            h, w = self.original_image.shape
            comparison = np.zeros((h, w * 2), dtype=np.uint8)
            comparison[:, :w] = self.original_image
            comparison[:, w:] = self.binarized_image

            # Convert to BGR for colored text
            comparison_bgr = cv2.cvtColor(comparison, cv2.COLOR_GRAY2BGR)

            # Add labels
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = min(1.0, w / 800)  # Scale font based on image width
            thickness = max(1, int(font_scale * 2))
            
            # Original image label
            cv2.putText(comparison_bgr, "Original", (10, 30), font, font_scale, (0, 255, 0), thickness)
            
            # Binarized image label with method info
            binary_label = f"Binarized ({self.method_info})" if self.method_info else "Binarized"
            cv2.putText(comparison_bgr, binary_label, (w + 10, 30), font, font_scale, (0, 255, 0), thickness)

            # Add pixel statistics
            if self.binarized_image is not None:
                white_pixels = np.sum(self.binarized_image == 255)
                black_pixels = np.sum(self.binarized_image == 0)
                total_pixels = self.binarized_image.size
                
                stats_text = f"White: {100*white_pixels/total_pixels:.1f}% | Black: {100*black_pixels/total_pixels:.1f}%"
                cv2.putText(comparison_bgr, stats_text, (w + 10, h - 20), font, font_scale * 0.7, (255, 255, 0), thickness)

            # Save the comparison image
            output_path = self._get_output_path(filename)
            cv2.imwrite(output_path, comparison_bgr)
            
        except Exception as e:
            # Silently fail to avoid disrupting the main pipeline
            pass
