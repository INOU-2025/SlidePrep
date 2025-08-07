import cv2
import numpy as np
from typing import Any, Optional, List
from utils.debug.base_drawer import BaseDrawer
from utils.detection.models import DetectionStrategy


class DetectionDrawer(BaseDrawer):
    """
    Debug drawer for adaptive line detection visualization.

    Creates comprehensive visualizations showing:
    - Detection results with strategy-specific coloring
    - Border zone overlays when applicable
    """

    def __init__(self, show_border_zones: bool = True):
        """
        Initialize the detection drawer.

        Args:
            show_border_zones: Whether to show border zone overlays
        """
        self.show_border_zones = show_border_zones

    def draw(self, image: np.ndarray, results: Any = None, metadata: Any = None) -> Optional[np.ndarray]:
        """Draw detection results on the image."""
        if results is None:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        # Convert to BGR for visualization
        base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        detections = results.get('detections', {}) if results else {}
        strategies = results.get('strategies', {}) if results else {}
        border_configs = metadata.get('border_configs', {}) if metadata else {}

        # Draw border overlay if any border strategy was used
        if self.show_border_zones and border_configs:
            max_border_thickness = 0
            for strategy, config in border_configs.items():
                max_border_thickness = max(max_border_thickness, config['border_thickness'])

            if max_border_thickness > 0:
                base = self._draw_border_overlay(base, max_border_thickness, alpha=0.15)

        # Draw detections for each orientation
        for orientation, contours in detections.items():
            if contours and strategies.get(orientation):
                strategy = strategies[orientation]
                base = self._draw_contours_with_strategy(base, contours, orientation, strategy)

        return base

    def _draw_border_overlay(self, image: np.ndarray, border_thickness: int, alpha: float = 0.25) -> np.ndarray:
        """
        Draw border zone overlay on image.

        Args:
            image: Input image
            border_thickness: Border zone thickness
            alpha: Overlay transparency (0-1)

        Returns:
            Image with border overlay
        """
        h, w = image.shape[:2]
        overlay = image.copy()

        # Ensure overlay is BGR
        if len(overlay.shape) == 2:
            overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)

        cv2.rectangle(overlay, (0, 0), (w, border_thickness), (0, 0, 255), -1)
        cv2.rectangle(overlay, (0, h - border_thickness),
                      (w, h), (0, 0, 255), -1)
        cv2.rectangle(overlay, (0, 0), (border_thickness, h), (0, 0, 255), -1)
        cv2.rectangle(overlay, (w - border_thickness, 0),
                      (w, h), (0, 0, 255), -1)

        # Ensure base image is BGR for blending
        base = image.copy()
        if len(base.shape) == 2:
            base = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)

        return cv2.addWeighted(overlay, alpha, base, 1 - alpha, 0)

    def _draw_contours_with_strategy(self, base_image: np.ndarray, contours: List[np.ndarray],
                                     orientation: str, strategy: DetectionStrategy) -> np.ndarray:
        """
        Draw contours with strategy-specific coloring.
        
        Note: Contours are pre-corrected and pre-filtered by the detector.

        Args:
            base_image: Base image to draw on
            contours: List of pre-corrected and pre-filtered contours to draw
            orientation: 'horizontal' or 'vertical'
            strategy: Detection strategy used

        Returns:
            Image with drawn contours
        """
        result = base_image.copy()
        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        h, w = result.shape[:2]

        for cnt in contours:
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.intp(box)

            # Since contours are pre-filtered by detector, all are valid
            # Just apply strategy-based coloring
            if strategy == DetectionStrategy.GENERAL:
                color = (0, 255, 0) if orientation == 'vertical' else (255, 0, 0)
            elif strategy == DetectionStrategy.THICK_BORDER:
                color = (0, 200, 0) if orientation == 'vertical' else (200, 0, 0)
            else:  # THIN_BORDER
                color = (0, 150, 0) if orientation == 'vertical' else (150, 0, 0)

            cv2.drawContours(result, [box], 0, color, 2)

        return result
