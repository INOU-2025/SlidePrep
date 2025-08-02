import cv2
import numpy as np
from typing import Optional, Callable


def apply_otsu_threshold(
    gray: np.ndarray,
    invert: bool = False,
    debug_callback: Optional[Callable[[str], None]] = None,
) -> np.ndarray:
    """
    Apply Otsu's automatic thresholding to a grayscale image.

    Otsu's method automatically determines the optimal threshold value by
    minimizing intra-class variance of the pixel intensities. This method
    works well for images with bimodal histograms where the foreground
    and background have distinct intensity distributions.

    The function supports both normal and inverted binary output depending
    on whether dark or light regions should be considered foreground.

    Args:
        gray: Grayscale input image as uint8 numpy array
        invert: If False, pixels below threshold become white (255).
               If True, pixels above threshold become white (255).
        debug_callback: Optional callback function for logging threshold information

    Returns:
        Binary image with values 0 and 255, where the assignment depends
        on the invert parameter and computed Otsu threshold.
    """
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
