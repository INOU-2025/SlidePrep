import cv2
import numpy as np
from typing import Tuple


class LineTemplateFactory:
    """
    Factory for creating line templates for grid detection in images.

    Creates binary template images containing straight lines of specified
    dimensions and orientations. These templates are used in template matching
    algorithms to detect grid patterns in binarized images. Supports both
    horizontal and vertical orientations with optional rotation.

    The factory generates templates with white lines (255) on black backgrounds (0)
    and can apply rotation to handle slightly skewed grid patterns. Template
    dimensions are automatically calculated based on line parameters.
    """

    def __init__(self, length: int = 40, thickness: int = 21, angle_deg: float = 2.0) -> None:
        """
        Initialize the line template factory with specified parameters.

        Args:
            length: Length of the line template in pixels. Must be positive.
            thickness: Thickness of the line template in pixels. Must be positive.
            angle_deg: Rotation angle in degrees for handling skewed lines.
                      Typically small values (e.g., ±2°) for grid detection.

        Raises:
            ValueError: If length or thickness are not positive integers.
        """
        if length <= 0 or thickness <= 0:
            raise ValueError("Length and thickness must be positive integers.")
        self.length = length
        self.thickness = thickness
        self.angle_deg = angle_deg

    def create(self, orientation: str = 'horizontal') -> np.ndarray:
        """
        Create a line template image for the specified orientation.

        Generates a binary template image containing a straight line of the
        configured dimensions. The template can be rotated by the specified
        angle to match slightly skewed grid patterns in source images.

        Args:
            orientation: Line orientation - either 'horizontal' or 'vertical'

        Returns:
            Binary numpy array containing the template with white line (255)
            on black background (0). Template size is (length + thickness) square.

        Raises:
            ValueError: If orientation is not 'horizontal' or 'vertical'.
        """
        size: Tuple[int, int] = (
            self.length + self.thickness, self.length + self.thickness)
        template: np.ndarray = np.zeros(size, dtype=np.uint8)

        if orientation == 'horizontal':
            start: Tuple[int, int] = (
                self.thickness // 2, size[1] // 2 - self.thickness // 2)
            end: Tuple[int, int] = (
                size[0] - self.thickness // 2, size[1] // 2 + self.thickness // 2)
        elif orientation == 'vertical':
            start = (size[0] // 2 - self.thickness // 2, self.thickness // 2)
            end = (size[0] // 2 + self.thickness //
                   2, size[1] - self.thickness // 2)
        else:
            raise ValueError("orientation must be 'horizontal' or 'vertical'")

        cv2.rectangle(template, start, end, 255, -1)
        center: Tuple[int, int] = (size[0] // 2, size[1] // 2)
        if self.angle_deg == 0.0:
            return template
        rot_mat: np.ndarray = cv2.getRotationMatrix2D(
            center, self.angle_deg, 1.0)
        rotated: np.ndarray = cv2.warpAffine(
            template, rot_mat, size, flags=cv2.INTER_LINEAR, borderValue=0)
        return rotated
