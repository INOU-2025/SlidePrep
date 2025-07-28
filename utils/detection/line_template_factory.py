import cv2
import numpy as np

class LineTemplateFactory:
    """
    Factory for creating line templates for grid/line detection.

    Parameters:
        length (int): Length of the line. Default is 40.
        thickness (int): Thickness of the line. Default is 21.
        angle_deg (float): Rotation angle in degrees. Default is 2.0.
    """

    length: int
    thickness: int
    angle_deg: float

    def __init__(self, length: int = 40, thickness: int = 21, angle_deg: float = 2.0) -> None:
        if length <= 0 or thickness <= 0:
            raise ValueError("Length and thickness must be positive integers.")
        self.length = length
        self.thickness = thickness
        self.angle_deg = angle_deg

    def create(self, orientation: str = 'horizontal') -> np.ndarray:
        """
        Create a line template.

        Parameters:
            orientation (str): 'horizontal' or 'vertical'

        Returns:
            np.ndarray: The template image.
        """
        size: tuple[int, int] = (self.length + self.thickness, self.length + self.thickness)
        template: np.ndarray = np.zeros(size, dtype=np.uint8)

        if orientation == 'horizontal':
            start: tuple[int, int] = (self.thickness // 2, size[1] // 2 - self.thickness // 2)
            end: tuple[int, int] = (size[0] - self.thickness // 2, size[1] // 2 + self.thickness // 2)
        elif orientation == 'vertical':
            start = (size[0] // 2 - self.thickness // 2, self.thickness // 2)
            end = (size[0] // 2 + self.thickness // 2, size[1] - self.thickness // 2)
        else:
            raise ValueError("orientation must be 'horizontal' or 'vertical'")

        cv2.rectangle(template, start, end, 255, -1)
        center: tuple[int, int] = (size[0] // 2, size[1] // 2)
        if self.angle_deg == 0.0:
            return template
        rot_mat: np.ndarray = cv2.getRotationMatrix2D(center, self.angle_deg, 1.0)
        rotated: np.ndarray = cv2.warpAffine(template, rot_mat, size, flags=cv2.INTER_LINEAR, borderValue=0)
        return rotated