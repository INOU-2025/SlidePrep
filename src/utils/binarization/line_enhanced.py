"""Line-enhanced thresholding using directional filter responses."""

import cv2
import numpy as np
from typing import Optional, Callable


def apply_line_enhanced_threshold(
    gray: np.ndarray,
    kernel_length: int = 21,
    rotation_angle: float = 2.0,
    invert: bool = False,
    debug_callback: Optional[Callable] = None,
) -> np.ndarray:
    """Apply line-enhanced thresholding for detecting linear structures."""
    angle_rad = np.radians(rotation_angle)
    h_kernel = np.zeros((kernel_length, kernel_length), dtype=np.float32)
    center = kernel_length // 2
    for i in range(kernel_length):
        x = i - center
        y = int(x * np.tan(angle_rad))
        if abs(y) <= center:
            h_kernel[center + y, i] = 1
    h_kernel /= np.sum(h_kernel)

    v_kernel = np.zeros((kernel_length, kernel_length), dtype=np.float32)
    for i in range(kernel_length):
        y = i - center
        x = int(y * np.tan(angle_rad))
        if abs(x) <= center:
            v_kernel[i, center + x] = 1
    v_kernel /= np.sum(v_kernel)

    h_response = cv2.filter2D(gray, -1, h_kernel)
    v_response = cv2.filter2D(gray, -1, v_kernel)
    line_enhanced = cv2.max(h_response, v_response)
    thresh_type = (
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        if not invert
        else cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    threshold_value, binary = cv2.threshold(line_enhanced, 0, 255, thresh_type)
    if debug_callback:
        debug_callback(
            f"Applied line-enhanced threshold: kernel={kernel_length}, angle={rotation_angle}°, threshold={threshold_value:.2f}"
        )
    return binary
