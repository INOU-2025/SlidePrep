"""Template generation and matching utilities for grid-line detection."""

import cv2
import numpy as np
from typing import List, Tuple


def generate_blurred_template(length: int, thickness: int, angle_deg: float, orientation: str) -> np.ndarray:
    """Generate a Gaussian-blurred line template.

    Args:
        orientation: 'horizontal' or 'vertical'
    """
    out_h, out_w = (thickness, length) if orientation == 'horizontal' else (length, thickness)

    if angle_deg == 0:
        template = np.zeros((out_h, out_w), dtype=np.uint8)
        cv2.rectangle(template, (0, 0), (out_w - 1, out_h - 1), 255, -1)
        return cv2.GaussianBlur(template, (5, 5), 0)

    # Draw on a canvas padded to the rotated bounding box so the line's ends
    # aren't clipped by the rotation, then crop back to the requested size.
    theta = np.radians(abs(angle_deg))
    pad_h = int(np.ceil(out_w * np.sin(theta) + out_h * np.cos(theta) - out_h)) + 2
    pad_w = int(np.ceil(out_w * np.cos(theta) + out_h * np.sin(theta) - out_w)) + 2

    top, left = pad_h // 2, pad_w // 2
    template = np.zeros((out_h + pad_h, out_w + pad_w), dtype=np.uint8)
    cv2.rectangle(template, (left, top), (left + out_w - 1, top + out_h - 1), 255, -1)
    template = cv2.GaussianBlur(template, (5, 5), 0)

    center = (template.shape[1] / 2, template.shape[0] / 2)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    template = cv2.warpAffine(template, M, (template.shape[1], template.shape[0]),
                              flags=cv2.INTER_LINEAR, borderValue=0)

    crop_top, crop_left = (template.shape[0] - out_h) // 2, (template.shape[1] - out_w) // 2
    return template[crop_top:crop_top + out_h, crop_left:crop_left + out_w]


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
