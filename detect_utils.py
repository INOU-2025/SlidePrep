import torch
import cv2
import numpy as np
import matplotlib.pyplot as plt
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

def cluster_group_positions(groups, orientation='horizontal', cluster_thresh=28, min_group_separation=15):
    axis = 0 if orientation == 'horizontal' else 1
    group_positions = []

    for group in groups:
        coords = [pt[axis] for seg in group for pt in seg]
        avg = sum(coords) / len(coords)
        group_positions.append(avg)

    sorted_indices = sorted(range(len(groups)), key=lambda i: group_positions[i])
    clusters = []

    for i, idx_i in enumerate(sorted_indices):
        pos_i = group_positions[idx_i]
        found_pair = False

        for j in range(i + 1, len(sorted_indices)):
            idx_j = sorted_indices[j]
            pos_j = group_positions[idx_j]
            dist = abs(pos_j - pos_i)

            if dist < min_group_separation:
                continue
            if dist > cluster_thresh:
                break

            clusters.append([idx_i, idx_j])
            found_pair = True

        if not found_pair:
            clusters.append([idx_i])

    # Deduplicate: remove clusters that are strict subsets of others
    unique_clusters = []
    seen_sets = []
    for cluster in clusters:
        s = set(cluster)
        if not any(s < seen for seen in seen_sets):  # strict subset
            unique_clusters.append(cluster)
            seen_sets.append(s)
    return unique_clusters, group_positions


def select_best_cluster(clusters, groups, verbose=False, logger=print):
    if not clusters:
        return []

    def cluster_score(cluster):
        # Adjusted for merged cluster dict format
        if isinstance(cluster, dict):
            num_groups = len(cluster['groups'])
            total_length = sum(
                np.linalg.norm(seg[0] - seg[1]) for seg in cluster['groups']
            )
        else:
            num_groups = len(cluster)
            total_length = sum(
                np.linalg.norm(seg[0] - seg[1]) for idx in cluster for seg in groups[idx]
            )
        return (num_groups, total_length)

    scored_clusters = [(cluster, cluster_score(cluster)) for cluster in clusters]
    sorted_clusters = sorted(scored_clusters, key=lambda x: (-x[1][0], -x[1][1]))

    if verbose:
        for i, (cluster, (num_groups, total_length)) in enumerate(sorted_clusters):
            logger(f"\nCluster {i}: groups={cluster if not isinstance(cluster, dict) else cluster['group_indices']}, num_groups={num_groups}, total_length={total_length:.1f}")
            if isinstance(cluster, dict):
                for seg in cluster['groups']:
                    (y0, x0), (y1, x1) = seg
                    logger(f"    Segment: ({x0:.1f}, {y0:.1f}) -> ({x1:.1f}, {y1:.1f})")
            else:
                for idx in cluster:
                    logger(f"  Group {idx}:")
                    for seg in groups[idx]:
                        (y0, x0), (y1, x1) = seg
                        logger(f"    Segment: ({x0:.1f}, {y0:.1f}) -> ({x1:.1f}, {y1:.1f})")

    return sorted_clusters[0][0]  # Best cluster (list of group indices or merged cluster dict)

def select_nonoverlapping_clusters(clusters, groups, positions, min_spacing=10, orientation='horizontal', image_shape=None, min_score=300):
    import math
    H, W = image_shape
    margin_ratio = 0.1
    border_margin = margin_ratio * (H if orientation == 'horizontal' else W)

    def count_segments(cluster):
        if isinstance(cluster, dict):
            return len(cluster['groups'])
        else:
            return sum(len(groups[idx]) for idx in cluster)

    def total_length(cluster):
        if isinstance(cluster, dict):
            return sum(segment_length(s) for s in cluster['groups'])
        else:
            return sum(segment_length(s) for idx in cluster for s in groups[idx])

    def span_extent(cluster):
        axis = 0 if orientation == 'horizontal' else 1
        if isinstance(cluster, dict):
            pts = [pt[axis] for seg in cluster['groups'] for pt in seg]
        else:
            pts = [pt[axis] for idx in cluster for seg in groups[idx] for pt in seg]
        return max(pts) - min(pts) if pts else 0

    def average_position(cluster):
        if isinstance(cluster, dict):
            return cluster['avg_pos']
        else:
            return np.mean([positions[idx] for idx in cluster])

    def near_border(avg_pos):
        return avg_pos < border_margin or avg_pos > ((H if orientation == 'horizontal' else W) - border_margin)

    scored = []
    for cl in clusters:
        n_segs = count_segments(cl)
        if n_segs < 1:
            continue
        length = total_length(cl)
        span = span_extent(cl)
        avg_pos = average_position(cl)
        border_bonus = 200 if near_border(avg_pos) else 0
        score = length + 20 * math.log(n_segs + 1) + 10 * span + border_bonus
        scored.append((cl, score))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[1])
    return [scored[0][0]] if scored[0][1] >= min_score else []

def merge_colinear_clusters(clusters, direction, groups, positions, max_pos_diff=30, max_angle_diff=3):
    """Merge clusters that are aligned but separated."""
    def compute_angle(segment):
        dx = segment[1][0] - segment[0][0]
        dy = segment[1][1] - segment[0][1]
        return np.arctan2(dy, dx) * 180 / np.pi

    merged = []
    used = set()

    for i, c1 in enumerate(clusters):
        if i in used:
            continue
        base_angle = compute_angle(groups[c1[0]][0])
        merged_cluster = {
            'group_indices': list(c1),
            'groups': [seg for idx in c1 for seg in groups[idx]],
            'avg_pos': positions[c1[0]]
        }

        for j, c2 in enumerate(clusters):
            if j <= i or j in used:
                continue
            c2_angle = compute_angle(groups[c2[0]][0])
            pos_diff = abs(float(merged_cluster['avg_pos']) - float(positions[c2[0]]))
            angle_diff = abs(base_angle - c2_angle)
            if pos_diff < max_pos_diff and angle_diff < max_angle_diff:
                merged_cluster['group_indices'].extend(c2)
                merged_cluster['groups'].extend([seg for idx in c2 for seg in groups[idx]])
                used.add(j)

        merged.append(merged_cluster)
        used.add(i)

    return merged

# ---------- Drawing ----------

def draw_segments(img, segments, color, thickness=1):
    img_out = img.copy()
    for (y0, x0), (y1, x1) in segments:
        pt1 = (int(round(x0)), int(round(y0)))
        pt2 = (int(round(x1)), int(round(y1)))
        cv2.line(img_out, pt1, pt2, color, thickness)
    return img_out

def draw_groups(image, groups, thickness=2):
    output = image.copy()
    cmap = plt.get_cmap('tab20')  # Up to 20 distinguishable colors
    num_colors = cmap.N

    for i, group in enumerate(groups):
        color_rgb = cmap(i % num_colors)[:3]  # RGB tuple in [0,1]
        color_bgr = tuple(int(255 * c) for c in reversed(color_rgb))  # Convert to BGR for OpenCV

        for segment in group:
            pt1 = (int(round(segment[0][1])), int(round(segment[0][0])))
            pt2 = (int(round(segment[1][1])), int(round(segment[1][0])))
            cv2.line(output, pt1, pt2, color_bgr, thickness)

    return output

def draw_clusters(img, groups, clusters, thickness=2):
    img_out = img.copy()
    for cluster in clusters:
        color = tuple(np.random.randint(80, 255, 3).tolist())
        for group_idx in cluster:
            for (y0, x0), (y1, x1) in groups[group_idx]:
                pt1 = (int(round(x0)), int(round(y0)))
                pt2 = (int(round(x1)), int(round(y1)))
                cv2.line(img_out, pt1, pt2, color, thickness)
    return img_out

def draw_selected_cluster(img, groups, cluster, color=(0, 255, 0), thickness=2):
    img_out = img.copy()
    if isinstance(cluster, dict):
        for seg in cluster['groups']:
            (y0, x0), (y1, x1) = seg
            pt1 = (int(round(x0)), int(round(y0)))
            pt2 = (int(round(x1)), int(round(y1)))
            cv2.line(img_out, pt1, pt2, color, thickness)
    else:
        for group_idx in cluster:
            for (y0, x0), (y1, x1) in groups[group_idx]:
                pt1 = (int(round(x0)), int(round(y0)))
                pt2 = (int(round(x1)), int(round(y1)))
                cv2.line(img_out, pt1, pt2, color, thickness)
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


def print_cluster_summary(clusters, positions, orientation='horizontal', logger=print):
    label = 'Y' if orientation == 'horizontal' else 'X'
    logger(f"\n{orientation.capitalize()} contour clusters:")

    for i, cluster in enumerate(clusters):
        if isinstance(cluster, dict):
            group_indices = cluster.get('group_indices', [])
        else:
            group_indices = cluster

        pos_values = [positions[idx] for idx in group_indices if isinstance(idx, int)]
        avg_pos = np.mean(pos_values)
        logger(f"  Cluster {i}:")
        logger(f"    - Group indices: {group_indices}")
        logger(f"    - Avg {label} position: {avg_pos:.1f}")
        logger(f"    - Position values: {[f'{positions[idx]:.1f}' for idx in group_indices if isinstance(idx, int)]}")

def passthrough_clusters(clusters, positions, logger, orientation):
    for i, cluster in enumerate(clusters):
        logger(f"Retaining cluster {i} ({orientation}): {cluster}")
    return clusters
