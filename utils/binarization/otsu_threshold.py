import cv2
import numpy as np
from typing import Optional, Callable


def apply_otsu_threshold(
    gray: np.ndarray,
    invert: bool = False,
    debug_callback: Optional[Callable] = None,
) -> np.ndarray:
    """Apply Otsu's automatic thresholding."""
    thresh_type = (
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        if not invert
        else cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    threshold_value, binary = cv2.threshold(gray, 0, 255, thresh_type)
    if debug_callback:
        debug_callback(
            f"Applied Otsu threshold: computed threshold={threshold_value:.2f} ({'inverted' if invert else 'normal'})"
        )
    return binary
