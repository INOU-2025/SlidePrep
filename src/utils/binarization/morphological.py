"""Morphological post-processing applied after Otsu thresholding."""

import cv2
import numpy as np
from typing import Optional, Callable

from .otsu_threshold import apply_otsu_threshold


def apply_morphological_threshold(
    gray: np.ndarray,
    operation: str = "close",
    kernel_size: int = 3,
    invert: bool = False,
    debug_callback: Optional[Callable] = None,
) -> np.ndarray:
    """Apply morphological operations after Otsu thresholding."""
    binary = apply_otsu_threshold(
        gray, invert=invert, debug_callback=debug_callback)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    operation_map = {
        "open": cv2.MORPH_OPEN,
        "close": cv2.MORPH_CLOSE,
        "gradient": cv2.MORPH_GRADIENT,
        "tophat": cv2.MORPH_TOPHAT,
        "blackhat": cv2.MORPH_BLACKHAT,
    }
    if operation not in operation_map:
        raise ValueError(f"Unknown morphological operation: {operation}")
    morph_op = operation_map[operation]
    result = cv2.morphologyEx(binary, morph_op, kernel)
    if debug_callback:
        debug_callback(
            f"Applied morphological {operation}: kernel_size={kernel_size}")
    return result
