import cv2
import numpy as np
from typing import List, Tuple
from core.container import Container
from utils.detection.models import DetectionRegion, Orientation
from typing import Optional
import csv


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
    corners = [(0,0), (W,0), (0,H), (W,H)]
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


def analyze_contour(contour: np.ndarray, orientation: Orientation, strategy=None, image_shape=None) -> dict:
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
    box = box.astype(np.intp)

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

    # Proximity metrics (if image_shape is provided)
    if image_shape is not None:
        H, W = image_shape[:2]
        corner_proximity = corner_proximity_from_box(box, W, H)
        border_proximity = border_proximity_from_box(box, W, H)
    else:
        corner_proximity = None
        border_proximity = None

    # Orientation mismatch
    orientation_mismatch = has_orientation_mismatch(orientation, computed_orientation)

    logger.debug(
        f"Contour analysis:\n"
        f"  Orientation (passed): {orientation.value}\n"
        f"  Orientation (computed): {computed_orientation.value}\n"
        f"  Orientation mismatch: {orientation_mismatch}\n"
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
        f"  Strategy: {getattr(strategy, 'value', strategy) if strategy else 'undefined'}\n"
        f"  Corner proximity: {corner_proximity if corner_proximity is not None else 'undefined'}\n"
        f"  Border proximity: {border_proximity if border_proximity is not None else 'undefined'}"
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
    passed = passed_orientation.value if hasattr(passed_orientation, 'value') else str(passed_orientation)
    computed = computed_orientation.value if hasattr(computed_orientation, 'value') else str(computed_orientation)
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
            analysis = analyze_contour(contour, orientation, strategy=strategy, image_shape=image_shape)
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
        image_aggregated = analyze_all_contours_for_image(results, image_shape=image_shape)
        for analysis in image_aggregated:
            analysis['filename'] = filename
            aggregated.append(analysis)
    return aggregated


def save_aggregated_analysis_to_csv(analysis_results, csv_path):
    """
    Save aggregated contour analysis results to a CSV file.
    Args:
        analysis_results: List of analysis result dicts (from analyze_all_contours_from_results)
        csv_path: Path to output CSV file
    """
    if not analysis_results:
        raise ValueError("No analysis results to save.")

    # Convert enums to their string value for CSV friendliness
    enum_fields = {"orientation", "computed_orientation", "strategy", "zone"}
    for row in analysis_results:
        for field in enum_fields:
                value = row.get(field)
                if hasattr(value, "value"):
                    row[field] = value.value

    # Use keys from the first result as CSV columns
    fieldnames = list(analysis_results[0].keys())
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in analysis_results:
            # Flatten any numpy arrays or lists for CSV compatibility
            flat_row = {k: (v.tolist() if hasattr(v, 'tolist') else v) for k, v in row.items()}
            writer.writerow(flat_row)
