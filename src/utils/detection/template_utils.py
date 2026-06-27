"""Template generation and matching utilities for grid-line detection."""

import cv2
import numpy as np
from typing import List, Tuple


def generate_blurred_template(length: int, thickness: int, angle_deg: float, orientation: str) -> np.ndarray:
    """Generate a Gaussian-blurred line template.

    Args:
        orientation: 'horizontal' or 'vertical'
    """
    if orientation == 'horizontal':
        template = np.zeros((thickness, length), dtype=np.uint8)
        cv2.rectangle(template, (0, 0), (length-1, thickness-1), 255, -1)
    else:
        template = np.zeros((length, thickness), dtype=np.uint8)
        cv2.rectangle(template, (0, 0), (thickness-1, length-1), 255, -1)

    template = cv2.GaussianBlur(template, (5, 5), 0)

    if angle_deg != 0:
        center = (template.shape[1] // 2, template.shape[0] // 2)
        M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
        template = cv2.warpAffine(template, M, (template.shape[1], template.shape[0]),
                                  flags=cv2.INTER_LINEAR, borderValue=0)
    return template


def pad_response(response: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
    """Pad or crop response to target_shape (height, width)."""
    pad_y = target_shape[0] - response.shape[0]
    pad_x = target_shape[1] - response.shape[1]
    return cv2.copyMakeBorder(response, 0, pad_y, 0, pad_x, cv2.BORDER_CONSTANT, value=1.0)


def perform_template_matching(image: np.ndarray, templates: List[np.ndarray]) -> np.ndarray:
    """
    Perform template matching with multiple templates and return minimum response.

    Args:
        image: Input image (should be inverted for line detection)
        templates: List of templates to match

    Returns:
        Combined minimum response map
    """
    responses = [pad_response(cv2.matchTemplate(image, tpl, cv2.TM_SQDIFF_NORMED), image.shape)
                 for tpl in templates]
    return np.minimum.reduce(responses)
