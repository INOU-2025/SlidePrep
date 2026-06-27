"""Combined differential thresholding — the primary production binarization method."""

import cv2
import numpy as np
from typing import Optional, Callable

from .multi_otsu import apply_multi_otsu_threshold


def apply_combined_differential_threshold(
    gray: np.ndarray,
    debug_callback: Optional[Callable] = None,
) -> np.ndarray:
    """Apply combined differential thresholding."""
    if debug_callback:
        debug_callback(
            "Applying combined differential threshold (multi_otsu - spurious elements)")
    multi_otsu_result = apply_multi_otsu_threshold(
        gray, debug_callback=debug_callback)
    total_black = np.sum(multi_otsu_result == 0)
    total_white = np.sum(multi_otsu_result == 255)
    if total_black > total_white:
        multi_otsu_result = cv2.bitwise_not(multi_otsu_result)
        if debug_callback:
            debug_callback("Applied polarity correction to multi_otsu")
    spurious_elements = _detect_spurious_elements(
        gray, multi_otsu_result, debug_callback)
    multi_otsu_fg = multi_otsu_result == 0
    spurious_fg = spurious_elements == 0
    clean_foreground = multi_otsu_fg & ~spurious_fg
    final_binary = np.where(clean_foreground, 0, 255).astype(np.uint8)
    if debug_callback:
        debug_callback(
            f"Multi-otsu foreground pixels: {np.sum(multi_otsu_fg)}")
        debug_callback(f"Spurious element pixels: {np.sum(spurious_fg)}")
        debug_callback(f"Clean foreground pixels: {np.sum(clean_foreground)}")
    return final_binary


def _detect_spurious_elements(
    gray: np.ndarray,
    multi_otsu_result: np.ndarray,
    debug_callback: Optional[Callable] = None,
) -> np.ndarray:
    """Detect spurious elements to remove from grid detection."""
    spurious_mask = np.zeros_like(gray, dtype=np.uint8)
    min_spurious_area = 300
    max_spurious_area = 1500
    max_aspect_ratio = 1.5
    connectivity = 8
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        cv2.bitwise_not(multi_otsu_result), connectivity=connectivity
    )
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        bbox_width = stats[i, cv2.CC_STAT_WIDTH]
        bbox_height = stats[i, cv2.CC_STAT_HEIGHT]
        aspect_ratio = max(bbox_width, bbox_height) / \
            max(min(bbox_width, bbox_height), 1)
        is_spurious = (
            min_spurious_area <= area <= max_spurious_area
            and aspect_ratio <= max_aspect_ratio
        )
        if is_spurious:
            component_mask = (labels == i).astype(np.uint8) * 255
            spurious_mask = cv2.bitwise_or(spurious_mask, component_mask)
    spurious_binary = cv2.bitwise_not(spurious_mask)
    if debug_callback:
        debug_callback(
            f"Detected spurious elements: {np.sum(spurious_binary == 0)} pixels"
        )
    return spurious_binary
