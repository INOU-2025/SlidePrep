import cv2
import numpy as np
from typing import List, Tuple
from src.core.container import Container
from src.utils.detection.models import DetectionRegion, Orientation, DetectionStrategy
from typing import Optional


def corner_proximity_from_box(box, W, H):
    """
    Normalized by FULL diagonal.
    0 = exactly on a corner, ~1 = near image center.
    Uses the min distance from any box vertex to any image corner.
    Args:
        box: Nx2 array of box vertices (e.g., from cv2.boxPoints)
        W: image width
        H: image height
    Returns:
        float: normalized proximity (0=corner, ~1=center)
    """
    FULL_DIAG = np.hypot(W, H)
    corners = [(0, 0), (W, 0), (0, H), (W, H)]
    dmin = min(
        np.hypot(px - cx, py - cy)
        for (px, py) in box
        for (cx, cy) in corners
    )
    return float(dmin / FULL_DIAG)


def border_proximity_from_box(box, W, H):
    """
    Normalized by max image dimension.
    0 = touching a border, ~0.5 = centered along the short dimension.
    Uses the min distance from any box vertex to the nearest border.
    Args:
        box: Nx2 array of box vertices (e.g., from cv2.boxPoints)
        W: image width
        H: image height
    Returns:
        float: normalized proximity (0=border, ~0.5=center)
    """
    MAX_DIM = max(W, H)
    dmin = min(min(x, W - x, y, H - y) for (x, y) in box)
    return float(dmin / MAX_DIM)


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
        box = box.astype(np.intp)
        zone = get_contour_zone(box, img_shape, border_thickness, orientation)

        if zone:
            filtered_contours.append({'contour': cnt, 'zone': zone})

    return filtered_contours


def analyze_contour(contour: np.ndarray, orientation: Orientation, strategy: DetectionStrategy = None, image_shape: Tuple[int, int] = None) -> dict:
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

    box_f = cv2.boxPoints(min_rect)
    box_i = box_f.astype(np.intp)

    width = float(rect_w)
    height = float(rect_h)

    edges = [(box_f[i], box_f[(i + 1) % 4]) for i in range(4)]
    lens = [np.linalg.norm(p2 - p1) for p1, p2 in edges]
    max_i = int(np.argmax(lens))
    p1, p2 = edges[max_i]
    long_side_angle = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))

    if long_side_angle >= 90:
        long_side_angle -= 180
    elif long_side_angle < -90:
        long_side_angle += 180

    aspect_ratio = width / height if height != 0 else 0
    length = max(width, height)

    if -45 <= long_side_angle <= 45:
        computed_orientation = Orientation.HORIZONTAL
    else:
        computed_orientation = Orientation.VERTICAL

    M = cv2.moments(contour)
    centroid = ((M["m10"] / M["m00"], M["m01"] / M["m00"])
                ) if M["m00"] != 0 else (0.0, 0.0)

    if image_shape is not None and strategy in [DetectionStrategy.THICK_BORDER, DetectionStrategy.THIN_BORDER]:
        H, W = image_shape[:2]
        corner_proximity = corner_proximity_from_box(box_i, W, H)
        border_proximity = border_proximity_from_box(box_i, W, H)
    else:
        corner_proximity = None
        border_proximity = None

    orientation_mismatch = has_orientation_mismatch(
        orientation, computed_orientation)

    logger.debug(
        f"Contour analysis:\n"
        f"  Orientation (passed): {orientation.value}\n"
        f"  Orientation (computed): {computed_orientation.value}\n"
        f"  Orientation mismatch: {orientation_mismatch}\n"
        f"  Area: {area:.3f}\n"
        f"  Perimeter: {perimeter:.3f}\n"
        f"  Min area rect: center=({cx:.3f}, {cy:.3f}), size=({rect_w:.3f}, {rect_h:.3f}), raw_angle={raw_angle:.3f}\n"
        f"  Longest side angle: {long_side_angle:.1f}\n"
        f"  Box points: {box_i.tolist()}\n"
        f"  Width: {width:.3f}, Height: {height:.3f}\n"
        f"  Aspect ratio: {aspect_ratio:.3f}\n"
        f"  Length: {length:.3f}\n"
        f"  Centroid: {centroid}\n"
        f"  Coordinates: {coordinates if len(coordinates) <= 10 else '[truncated]'}\n"
        f"  Strategy: {getattr(strategy, 'value', strategy) if strategy else 'undefined'}\n"
        f"  Corner proximity: {corner_proximity if corner_proximity is not None else 'undefined'}\n"
        f"  Border proximity: {border_proximity if border_proximity is not None else 'undefined'}"
    )

    return {
        "coordinates": coordinates,
        "area": area,
        "perimeter": perimeter,
        "min_area_rect": min_rect,
        "box_points": box_i.tolist(),
        "width": width,
        "height": height,
        "aspect_ratio": aspect_ratio,
        "length": length,
        "orientation": orientation,
        "computed_orientation": computed_orientation,
        "raw_angle": raw_angle,
        "long_side_angle": long_side_angle,
        "centroid": centroid,
        "strategy": strategy,
        "corner_proximity": corner_proximity,
        "border_proximity": border_proximity,
        "orientation_mismatch": orientation_mismatch
    }


def has_orientation_mismatch(passed_orientation, computed_orientation):
    """
    Returns True if there is a mismatch between the passed and computed orientation.
    Args:
        passed_orientation: Orientation enum or string
        computed_orientation: Orientation enum or string
    Returns:
        bool: True if mismatch, False otherwise
    """
    # Normalize to string for comparison
    passed = passed_orientation.value if hasattr(
        passed_orientation, 'value') else str(passed_orientation)
    computed = computed_orientation.value if hasattr(
        computed_orientation, 'value') else str(computed_orientation)
    return passed != computed


def analyze_all_contours_for_image(results, image_shape=None):
    """
    Iterate through contours in grid detection results obtained for am image and analyze each contour.
    Args:
        results: dict with 'detections' (orientation -> list of contour dicts)
        image_shape: tuple (height, width) of image (optional, for proximity metrics)
    Returns:
        List of aggregated analysis results for all contours.
    """
    aggregated = []
    detections = results.get('detections', {})
    for orientation, contour_dicts in detections.items():
        for item in contour_dicts:
            contour = item['contour']
            zone = item.get('zone', None)
            # Pass orientation as enum or string, strategy if available
            strategy = results.get('strategies', {}).get(orientation, None)
            analysis = analyze_contour(
                contour, orientation, strategy=strategy, image_shape=image_shape)
            analysis['zone'] = zone
            aggregated.append(analysis)
    return aggregated


def analyze_all_contours_for_batch(batch_results, image_shape=None):
    """
    Analyze all contours for a batch of images, assuming a common image_shape.

    Args:
        batch_results: List of dicts, each with 'filename' and 'result' (grid detection output).
        image_shape: tuple (height, width) for proximity metrics (applied to all images).

    Returns:
        List of aggregated analysis results for all contours in all images.
        Each result dict will include a 'filename' field for traceability.
    """
    aggregated = []
    for i, item in enumerate(batch_results):
        results = item.get('result')
        filename = item.get('filename', f"image_{i}")
        image_aggregated = analyze_all_contours_for_image(
            results, image_shape=image_shape)
        for analysis in image_aggregated:
            analysis['filename'] = filename
            aggregated.append(analysis)
    return aggregated
