import cv2
import numpy as np
from typing import Optional, Callable


def apply_global_threshold(
    gray: np.ndarray,
    threshold: int = 127,
    invert: bool = False,
    debug_callback: Optional[Callable] = None,
) -> np.ndarray:
    """Apply global (fixed) thresholding."""
    thresh_type = cv2.THRESH_BINARY_INV if not invert else cv2.THRESH_BINARY
    _, binary = cv2.threshold(gray, threshold, 255, thresh_type)
    if debug_callback:
        debug_callback(
            f"Applied global threshold: {threshold} ({'inverted' if invert else 'normal'})"
        )
    return binary
