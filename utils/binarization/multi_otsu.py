import numpy as np
from typing import Optional, Callable


def apply_multi_otsu_threshold(
    gray: np.ndarray,
    classes: int = 3,
    invert: bool = False,
    debug_callback: Optional[Callable] = None,
) -> np.ndarray:
    """Apply multi-level Otsu thresholding."""
    try:
        from skimage.filters import threshold_multiotsu

        thresholds = threshold_multiotsu(gray, classes=classes)
        if not invert:
            binary = np.ones_like(gray) * 255
            binary[gray <= thresholds[0]] = 0
        else:
            binary = np.zeros_like(gray)
            binary[gray <= thresholds[0]] = 255
        if debug_callback:
            debug_callback(
                f"Applied multi-Otsu thresholds: {[f'{t:.1f}' for t in thresholds]} ({'inverted' if invert else 'normal'})"
            )
        return binary
    except ImportError:
        if debug_callback:
            debug_callback("scikit-image not available, falling back to regular Otsu")
        from .otsu_threshold import apply_otsu_threshold

        return apply_otsu_threshold(gray, invert=invert, debug_callback=debug_callback)
