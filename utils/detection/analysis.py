# utils/detection/analysis.py

import numpy as np
import cv2
from typing import Tuple

from utils.detection.helpers import compute_min_required_ratio, border_touch_ratio


def draw_and_analyze_contour(
    contour,
    gray_image,
    line_orientation,
    position_offset,
    detection_thresholds,
    detection_drawer,
    filename,
    border_margin,
    logger
) -> Tuple[int, int, int]:
    """
    Draws a rotated box and the original contour, analyzes it, and logs detection statistics.

    Args:
        contour: Detected contour.
        gray_image: Grayscale image.
        line_orientation: 'horizontal' or 'vertical'.
        position_offset: Offset to correct position after template matching.
        detection_thresholds: Dictionary with thresholds.
        detection_drawer: GridDetectionDrawer instance.
        filename: Filename for logging.
        border_margin: Margin for border contact.
        logger: Logger instance.

    Returns:
        Tuple[int, int, int]: (accepted, rejected, maybe)
    """
    contour += position_offset
    area = cv2.contourArea(contour)
    if area == 0:
        return 0, 0, 0

    rotated_rect = cv2.minAreaRect(contour)
    rotated_box = cv2.boxPoints(rotated_rect).astype(np.intp)
    detection_drawer.draw_box(rotated_box, color=(0, 255, 255), thickness=1)

    mask = np.zeros_like(gray_image, dtype=np.uint8)
    cv2.fillPoly(mask, [rotated_box], 1)
    dark_ratio = np.count_nonzero((gray_image == 0) & (mask == 1)) / max(np.count_nonzero(mask), 1)

    contour_mask = np.zeros_like(gray_image, dtype=np.uint8)
    cv2.drawContours(contour_mask, [contour], -1, 1, -1)
    contour_dark_ratio = np.count_nonzero((gray_image == 0) & (contour_mask == 1)) / max(np.count_nonzero(contour_mask), 1)

    min_ratio = compute_min_required_ratio(area)
    (_, _), (w, h), raw_angle = rotated_rect
    angle = raw_angle + 90 if w < h else raw_angle
    angle = ((angle + 180) % 180) - 90
    length = max(w, h)
    angle_valid = (-4 <= angle <= 4) or (86 <= abs(angle) <= 94)

    accepted, maybe, decision = False, False, "REJECT"
    touches, ratio = -1, -1.0

    if dark_ratio >= 0.93:
        accepted, decision = True, "ACCEPT (high confidence)"
    elif dark_ratio < 0.73:
        decision = "REJECT (low confidence)"
    else:
        maybe = True
        decision = "MAYBE (edge case)"
        if length >= detection_thresholds['length']:
            accepted, maybe, decision = True, False, "ACCEPT (length override)"
        elif not angle_valid:
            maybe, decision = False, "REJECT (angle out of bounds)"

    if maybe:
        maybe = False
        touches, ratio = border_touch_ratio(rotated_box, line_orientation, gray_image.shape, border_margin)
        if contour_dark_ratio > 0.96 and dark_ratio >= 0.83:
            accepted, decision = True, "ACCEPT (contour ratio override)"
        elif contour_dark_ratio < 0.85 and dark_ratio < 0.80:
            decision = "REJECT (contour ratio override)"
        elif contour_dark_ratio >= 0.80 and dark_ratio >= 0.70 and touches and ratio > 0.9:
            accepted, decision = True, "ACCEPT (relaxed contour-touch override)"
        else:
            accepted, decision = False, "REJECT (not enough evidences)"

    detection_drawer.draw_contour(contour, accepted=accepted, maybe=maybe)
    logger.debug(
        f"{filename},{area:.1f},{dark_ratio:.3f},{contour_dark_ratio:.3f},{min_ratio:.3f},"
        f"{length:.1f},{line_orientation},{angle:.2f},{decision},{int(touches)},{ratio:.2f}"
    )

    return int(accepted), int(not accepted and not maybe), int(maybe)