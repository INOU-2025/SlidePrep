import torch
import cv2
import numpy as np
from typing import List, Tuple
import networkx as nx
from itertools import combinations

# ---------- Geometry & Segment Utilities ----------

def compute_angle_deg(seg):
    (y0, x0), (y1, x1) = seg
    dy = y1 - y0
    dx = x1 - x0
    angle_rad = np.arctan2(dy, dx)
    angle_deg = np.degrees(angle_rad)
    return angle_deg % 180  # Normalize to [0, 180)

def preprocess_for_sold2(img_bgr):
    # Convert to grayscale
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    contrast_maxed = cv2.convertScaleAbs(img_gray, alpha=3.0, beta=0)
    # Sharpening kernel
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    sharpened_once = cv2.filter2D(contrast_maxed, -1, kernel)
    sharpened_twice = cv2.filter2D(sharpened_once, -1, kernel)
    # Convert to normalized float32 tensor for Kornia
    img_tensor = torch.from_numpy(sharpened_twice).float()[None, None] / 255.0  # shape [1,1,H,W]
    return img_tensor

def segment_length(seg):
    return np.linalg.norm(seg[0] - seg[1])

# ---------- Grouping and Clustering ----------

def segment_angle(v1: np.ndarray, v2: np.ndarray) -> float:
    v1n = v1 / np.linalg.norm(v1)
    v2n = v2 / np.linalg.norm(v2)
    return np.degrees(np.arccos(np.clip(np.dot(v1n, v2n), -1.0, 1.0)))

def point_line_distance(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    return abs((b[1] - a[1]) * p[0] - (b[0] - a[0]) * p[1] + b[0]*a[1] - b[1]*a[0]) / np.linalg.norm(b - a)


def group_approximately_collinear_segments(
    segments: List[Tuple[np.ndarray, np.ndarray]],
    angle_thresh_deg: float = 2.0,
    distance_thresh_px: float = 5.0
) -> List[List[Tuple[np.ndarray, np.ndarray]]]:
    """
    Groups approximately collinear segments using angular and positional thresholds.

    Args:
        segments: List of segments, each as a tuple of two np.ndarray points (shape (2,), format (y, x)).
        angle_thresh_deg: Max angle difference between segment directions (in degrees).
        distance_thresh_px: Max midpoint-to-line distance for grouping.

    Returns:
        List of groups, where each group is a list of segments in (y, x) format.
    """
    seg_xy = [(p[::-1], q[::-1]) for p, q in segments]  # (x, y) for geometry
    G = nx.Graph()
    G.add_nodes_from(range(len(segments)))

    for i, j in combinations(range(len(segments)), 2):
        p1, q1 = seg_xy[i]
        p2, q2 = seg_xy[j]
        v1 = q1 - p1
        v2 = q2 - p2

        angle = segment_angle(v1, v2)
        if angle > angle_thresh_deg:
            continue

        midpoint_j = (p2 + q2) / 2
        dist = point_line_distance(midpoint_j, p1, q1)

        if dist < distance_thresh_px:
            G.add_edge(i, j)

    # Extract connected components using networkx
    connected = list(nx.connected_components(G))

    grouped_segments = [
        [segments[idx] for idx in component]
        for component in connected
    ]

    return grouped_segments


def identify_thick_line_groups(groups, orientation='horizontal', min_thickness=18.0, max_thickness=22.0,
                               min_segment_count=2):
    """
    Identify groups that define a thick line.

    Parameters:
        groups (list): List of groups, each a list of (pt1, pt2) segment tuples.
        orientation (str): 'horizontal' or 'vertical'.
        min_thickness (float): Minimum distance between parallel groups to qualify.
        max_thickness (float): Maximum distance allowed.
        min_segment_count (int): Minimum number of segments required per group.

    Returns:
        List of 1 or 2 groups representing the thick line.
    """
    axis = 0 if orientation == 'horizontal' else 1
    positions = []

    for group in groups:
        coords = [pt[axis] for seg in group for pt in seg]
        mean = np.mean(coords)
        positions.append(mean)

    sorted_indices = np.argsort(positions)

    # Try to find a pair of groups at the right distance
    for i in range(len(sorted_indices)):
        idx_i = sorted_indices[i]
        gi = groups[idx_i]
        pi = positions[idx_i]
        for j in range(i + 1, len(sorted_indices)):
            idx_j = sorted_indices[j]
            gj = groups[idx_j]
            pj = positions[idx_j]
            distance = abs(pj - pi)
            if min_thickness <= distance <= max_thickness:
                if len(gi) >= min_segment_count and len(gj) >= min_segment_count:
                    return [gi, gj]

    # Otherwise, check for single group with large span
    for group in groups:
        coords = [pt[axis] for seg in group for pt in seg]
        span = max(coords) - min(coords)
        if span >= min_thickness:
            return [group]

    return []

# ---------- Drawing ----------

def draw_lines(img, segments, color, thickness=1):
    img_out = img.copy()
    for (y0, x0), (y1, x1) in segments:
        pt1 = (int(round(x0)), int(round(y0)))
        pt2 = (int(round(x1)), int(round(y1)))
        cv2.line(img_out, pt1, pt2, color, thickness)
    return img_out

def draw_groups(image, groups, thickness=2):
    output = image.copy()
    # Use a fixed set of colors similar to tab20 but hardcoded to avoid matplotlib
    colors_bgr = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
        (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0),
        (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128),
        (64, 0, 0), (0, 64, 0), (0, 0, 64), (64, 64, 0),
        (64, 0, 64), (0, 64, 64), (192, 192, 192), (128, 128, 128)
    ]
    num_colors = len(colors_bgr)

    for i, group in enumerate(groups):
        color_bgr = colors_bgr[i % num_colors]

        for segment in group:
            pt1 = (int(round(segment[0][1])), int(round(segment[0][0])))
            pt2 = (int(round(segment[1][1])), int(round(segment[1][0])))
            cv2.line(output, pt1, pt2, color_bgr, thickness)

    return output

def draw_clusters(img, clusters, thickness=2):
    img_out = img.copy()
    color = (0, 255, 0)  # Green in BGR
    for cluster in clusters:
        for (pt1, pt2) in cluster:
            p1 = (int(round(pt1[1])), int(round(pt1[0])))
            p2 = (int(round(pt2[1])), int(round(pt2[0])))
            cv2.line(img_out, p1, p2, color, thickness)
    return img_out

# ---------- Reporting ----------

def print_colinear_groups(groups, orientation='horizontal', logger=print):
    axis = 0 if orientation == 'horizontal' else 1

    for i, group in enumerate(groups):
        coords = [pt[axis] for seg in group for pt in seg]
        min_val, max_val = min(coords), max(coords)
        mean_val = sum(coords) / len(coords)

        logger(f"\nGroup {i}:")
        logger(f"  - Segments: {len(group)}")
        logger(f"  - Span along {'Y' if axis == 0 else 'X'}: {min_val:.1f} to {max_val:.1f}")
        logger(f"  - Avg {'Y' if axis == 0 else 'X'} position: {mean_val:.1f}")
        logger(f"  - Segment coordinates:")

        for j, seg in enumerate(group):
            (y0, x0), (y1, x1) = seg
            logger(f"    {j}: ({x0:.1f}, {y0:.1f}) → ({x1:.1f}, {y1:.1f})")


def print_cluster_summary(clusters, orientation='horizontal', logger=print):
    label = 'Y' if orientation == 'horizontal' else 'X'
    logger(f"\n{orientation.capitalize()} contour clusters:")

    for i, cluster in enumerate(clusters):
        coords = [pt[0 if orientation == 'horizontal' else 1] for seg in cluster for pt in seg]
        if not coords:
            continue
        avg_pos = np.mean(coords)
        span = max(coords) - min(coords)

        logger(f"  Cluster {i}:")
        logger(f"    - Segments: {len(cluster)}")
        logger(f"    - Avg {label} position: {avg_pos:.1f}")
        logger(f"    - Span: {span:.1f}")
