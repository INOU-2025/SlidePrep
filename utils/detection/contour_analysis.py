import cv2
import numpy as np
from typing import List, Tuple


def contour_fully_within_zone(box: np.ndarray, img_shape: Tuple[int, int],
                              border_thickness: int, orientation: str) -> bool:
    """
    Check if a contour bounding box is fully within border zone.

    Args:
        box: Bounding box points
        img_shape: Image (height, width)
        border_thickness: Border zone thickness
        orientation: 'horizontal' or 'vertical'

    Returns:
        True if contour is fully within appropriate border zone
    """
    h, w = img_shape
    if orientation == 'horizontal':
        in_top = all(y < border_thickness for _, y in box)
        in_bottom = all(y >= h - border_thickness for _, y in box)
        return in_top or in_bottom
    elif orientation == 'vertical':
        in_left = all(x < border_thickness for x, _ in box)
        in_right = all(x >= w - border_thickness for x, _ in box)
        return in_left or in_right
    return False


def filter_contours_by_area(contours: List[np.ndarray], min_area: int) -> List[np.ndarray]:
    """
    Filter contours by minimum area.

    Args:
        contours: List of contours
        min_area: Minimum area threshold

    Returns:
        Filtered list of contours
    """
    return [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]


def filter_contours_by_border_zone(contours: List[np.ndarray], img_shape: Tuple[int, int],
                                   border_thickness: int, orientation: str) -> List[np.ndarray]:
    """
    Filter contours to only those within border zones.
    
    Note: Area filtering is now handled by the detector, so removed min_area parameter.

    Args:
        contours: List of contours (should already be area-filtered)
        img_shape: Image shape (height, width)
        border_thickness: Border zone thickness
        orientation: 'horizontal' or 'vertical'

    Returns:
        Filtered list of contours
    """
    filtered_contours = []

    for cnt in contours:
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.intp(box)

        if contour_fully_within_zone(box, img_shape, border_thickness, orientation):
            filtered_contours.append(cnt)

    return filtered_contours

