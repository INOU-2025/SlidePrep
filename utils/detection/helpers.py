import numpy as np
from typing import Tuple


def compute_min_required_ratio(area: float) -> float:
    """
    Compute the minimum required dark pixel ratio based on contour area.

    Args:
        area: Area of the contour

    Returns:
        Minimum acceptable ratio of dark pixels within the region
    """
    if area >= 9500:
        return 0.85
    if area <= 2000:
        return 0.96
    return 0.96 - 0.11 * ((area - 2000) / 7500)


def border_touch_ratio(rotated_box: np.ndarray, orientation: str, shape: tuple[int, int], margin: int) -> tuple[int, float]:
    """
    Compute whether a rotated bounding box touches the image border along its long edges.

    Args:
        rotated_box: Array of 4 points defining the rotated rectangle
        orientation: 'horizontal' or 'vertical' key defining expected orientation
        shape: Shape of the image (height, width)
        margin: Tolerance in pixels for considering an edge as touching the border

    Returns:
        Tuple of (1 if any long edge touches border, ratio of overlap samples that touch)
    """
    h, w = shape
    pts = rotated_box
    edges = [(pts[i], pts[(i + 1) % 4]) for i in range(4)]
    long_edges = sorted(edges, key=lambda e: -np.linalg.norm(e[0] - e[1]))[:2]

    max_overlap = 0.0
    for p1, p2 in long_edges:
        num_samples = int(np.linalg.norm(p1 - p2))
        if num_samples == 0:
            continue
        xs = np.linspace(p1[0], p2[0], num_samples)
        ys = np.linspace(p1[1], p2[1], num_samples)

        if orientation == "horizontal":
            match = (np.abs(ys) < margin) | (np.abs(ys - h) < margin)
        elif orientation == "vertical":
            match = (np.abs(xs) < margin) | (np.abs(xs - w) < margin)
        else:
            continue

        max_overlap = max(max_overlap, np.sum(match))

    return int(max_overlap > 0), max_overlap / num_samples if num_samples > 0 else 0.0
