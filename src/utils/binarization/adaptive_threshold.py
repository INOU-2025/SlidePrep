"""Adaptive (local) thresholding for binarization."""

import cv2
import numpy as np
from typing import Optional, Callable


def apply_adaptive_threshold(
    gray: np.ndarray,
    method: str = "gaussian",
    thresh_type: str = "binary",
    block_size: int = 11,
    c_constant: float = 2,
    invert: bool = False,
    debug_callback: Optional[Callable] = None,
) -> np.ndarray:
    """Apply adaptive thresholding."""
    adaptive_method = (
        cv2.ADAPTIVE_THRESH_MEAN_C
        if method == "mean"
        else cv2.ADAPTIVE_THRESH_GAUSSIAN_C
    )
    threshold_type = (
        cv2.THRESH_BINARY_INV if thresh_type == "binary_inv" else cv2.THRESH_BINARY
    )
    binary = cv2.adaptiveThreshold(
        gray, 255, adaptive_method, threshold_type, block_size, c_constant
    )
    if invert:
        binary = cv2.bitwise_not(binary)
    if debug_callback:
        debug_callback(
            f"Applied adaptive threshold: {method}, block_size={block_size}, C={c_constant}"
        )
    return binary
