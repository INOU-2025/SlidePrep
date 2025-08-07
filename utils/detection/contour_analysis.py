import cv2
import numpy as np
from typing import List, Tuple
from core.container import Container
from utils.detection.models import DetectionRegion, Orientation
from typing import Optional


def get_contour_zone(box: np.ndarray, img_shape: Tuple[int, int],
                     border_thickness: int, orientation: Orientation) -> Optional[DetectionRegion]:
    """
    Get the border zone that encloses a given contour

    Args:
        box: Bounding box points
        img_shape: Image (height, width)
        border_thickness: Border zone thickness
        orientation: Orientation of the contour ('horizontal' or 'vertical')

    Returns:
        True if contour is fully within appropriate border zone
    """
    h, w = img_shape
    if orientation == Orientation.HORIZONTAL:
        if all(y < border_thickness for _, y in box):
            return DetectionRegion.TOP
        elif all(y >= h - border_thickness for _, y in box):
            return DetectionRegion.BOTTOM
    elif orientation == Orientation.VERTICAL:
        if all(x < border_thickness for x, _ in box):
            return DetectionRegion.LEFT
        elif all(x >= w - border_thickness for x, _ in box):
            return DetectionRegion.RIGHT
    return None


def filter_contours_by_area(contours: List[np.ndarray], min_area: int) -> List[np.ndarray]:
    """
    Filter contours by minimum area.

    Args:
        contours: List of contours
        min_area: Minimum area threshold

    Returns:
        Filtered list of contours
    """
    return [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]


def filter_contours_by_border_zone(contours: List[np.ndarray], img_shape: Tuple[int, int],
                                   border_thickness: int, orientation: Orientation) -> List[dict]:
    """
    Filter contours to only those within border zones.

    Note: Area filtering is now handled by the detector, so removed min_area parameter.

    Args:
        contours: List of contours (should already be area-filtered)
        img_shape: Image shape (height, width)
        border_thickness: Border zone thickness
        orientation: Orientation of the contour ('horizontal' or 'vertical')

    Returns:
        Filtered list of contours
    """
    filtered_contours = []

    for cnt in contours:
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.intp(box)
        zone = get_contour_zone(box, img_shape, border_thickness, orientation)

        if zone:
            filtered_contours.append({'contour': cnt, 'zone': zone})

    return filtered_contours


def analyze_contour(contour: np.ndarray, orientation: Orientation, strategy=None) -> dict:
    """
    Analyze a contour and return analytical information.

    Args:
        contour: np.ndarray representing the contour
        orientation: Orientation of the contour (HORIZONTAL or VERTICAL)

    Returns:
        Dictionary with contour properties, including orientation.
    """
    logger = Container.resolve("logger")

    coordinates = contour.squeeze().tolist()
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)

    min_rect = cv2.minAreaRect(contour)
    ((cx, cy), (rect_w, rect_h), raw_angle) = min_rect
    box = cv2.boxPoints(min_rect)
    box = np.intp(box)

    # Calculate side lengths and find the longest side
    side_lengths = [np.linalg.norm(box[i] - box[(i + 1) % 4])
                    for i in range(4)]
    max_idx = np.argmax(side_lengths)
    pt1, pt2 = box[max_idx], box[(max_idx + 1) % 4]
    dx, dy = pt2[0] - pt1[0], pt2[1] - pt1[1]
    long_side_angle = np.degrees(np.arctan2(dy, dx))

    # Normalize angle to [-90, 90)
    if long_side_angle >= 90:
        long_side_angle -= 180
    elif long_side_angle < -90:
        long_side_angle += 180

    width = max(side_lengths)
    height = min(side_lengths)
    aspect_ratio = width / height if height != 0 else 0
    length = width

    # Compute orientation based on longest side angle
    if -45 <= long_side_angle <= 45:
        computed_orientation = Orientation.HORIZONTAL
    else:
        computed_orientation = Orientation.VERTICAL

    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity = area / hull_area if hull_area != 0 else 0
    extent = area / (width * height) if width * height != 0 else 0

    M = cv2.moments(contour)
    centroid = (int(M["m10"] / M["m00"]), int(M["m01"] /
                M["m00"])) if M["m00"] != 0 else (0, 0)

    logger.debug(
        f"Contour analysis:\n"
        f"  Orientation (passed): {orientation.value}\n"
        f"  Orientation (computed): {computed_orientation.value}\n"
        f"  Area: {area}\n"
        f"  Perimeter: {perimeter}\n"
        f"  Min area rect: center=({cx:.1f}, {cy:.1f}), size=({rect_w:.1f}, {rect_h:.1f}), raw_angle={raw_angle:.1f}\n"
        f"  Longest side angle: {long_side_angle:.1f}\n"
        f"  Box points: {box.tolist()}\n"
        f"  Width: {width:.1f}, Height: {height:.1f}\n"
        f"  Aspect ratio: {aspect_ratio:.3f}\n"
        f"  Length: {length:.1f}\n"
        f"  Solidity: {solidity:.3f}\n"
        f"  Extent: {extent:.3f}\n"
        f"  Centroid: {centroid}\n"
        f"  Coordinates: {coordinates if len(coordinates) <= 10 else '[truncated]'}\n"
        f"  Strategy: {getattr(strategy, 'value', strategy) if strategy else 'undefined'}"
    )

    return {
        "coordinates": coordinates,
        "area": area,
        "perimeter": perimeter,
        "min_area_rect": min_rect,
        "box_points": box.tolist(),
        "width": width,
        "height": height,
        "aspect_ratio": aspect_ratio,
        "length": length,
        "orientation": orientation,
        "computed_orientation": computed_orientation,
        "raw_angle": raw_angle,
        "long_side_angle": long_side_angle,
        "solidity": solidity,
        "extent": extent,
        "centroid": centroid,
        "strategy": strategy
    }
