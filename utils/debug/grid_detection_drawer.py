import cv2
import numpy as np
from typing import Optional, Any

from .base_drawer import BaseDrawer
from utils.detection import DetectionStatus, GridDetectionResult


class GridDetectionDrawer(BaseDrawer):
    """
    Specialized drawer for grid detection step debugging.
    Draws contours, bounding boxes, and detection results on the provided image.
    """

    def draw(self, image: np.ndarray, results: Any = None, metadata: Any = None) -> Optional[np.ndarray]:
        """
        Draw grid detection results on the image.

        Args:
            image: Base image to draw on (BGR format)
            results: GridDetectionResult with detections
            metadata: Additional metadata (unused)

        Returns:
            Image with drawn grid detection visualizations
        """
        if results is None or not isinstance(results, GridDetectionResult):
            return image.copy()

        canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if len(
            image.shape) == 2 else image.copy()

        for detection in results.detections:
            color = DetectionStatus.get_color(detection.status)

            cv2.drawContours(canvas, [detection.contour], 0, color, 2)

            if detection.rotated_box.size > 0:
                cv2.drawContours(canvas, [detection.rotated_box], 0, color, 1)

        return canvas

    def draw_box(self, box: np.ndarray, color: tuple = (255, 0, 0), thickness: int = 1) -> None:
        """Legacy method - consider using draw() instead."""
        pass

    def draw_contour(self, contour: np.ndarray, accepted: bool = False, maybe: bool = False) -> None:
        """Legacy method - consider using draw() instead."""
        pass
