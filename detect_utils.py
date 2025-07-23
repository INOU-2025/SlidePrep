import torch
import cv2
import numpy as np
import matplotlib.pyplot as plt

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

def group_colinear_segments_by_midpoint_projection(segments, distance_thresh=5, projection_margin=5, logger=print):
    from collections import deque
    segments = sorted(segments, key=lambda seg: -np.linalg.norm(seg[1] - seg[0]))
    remaining = deque(segments)
    groups = []

    while remaining:
        base = remaining.popleft()
        base_pt = base[0]
        direction = base[1] - base[0]
        direction = direction / np.linalg.norm(direction)
        normal = np.array([-direction[1], direction[0]])

        def point_to_line_dist(pt):
            vec = pt - base_pt
            return abs(np.dot(vec, normal))

        def project(pt):
            return np.dot(pt - base_pt, direction)

        group = [base]
        to_remove = []

        for i, seg in enumerate(remaining):
            p0, p1 = seg

            logger(f"🔍 Comparing to base segment:")
            logger(f"    Base: ({base[0][0]:.1f}, {base[0][1]:.1f}) → ({base[1][0]:.1f}, {base[1][1]:.1f})")
            logger(f"    Cand: ({p0[0]:.1f}, {p0[1]:.1f}) → ({p1[0]:.1f}, {p1[1]:.1f})")

            # 1. Orthogonal alignment check (both endpoints)
            d0 = point_to_line_dist(p0)
            d1 = point_to_line_dist(p1)

            logger(f"    Point 0 distance: {d0:.2f}")
            logger(f"    Point 1 distance: {d1:.2f}")

            if d0 > distance_thresh or d1 > distance_thresh:
                logger("    → Rejected: one or both points too far from base line.\n")
                continue
            else:
                logger("    → Accepted (passes orthogonal distance check).\n")

            # 2. Projection span check — reject if endpoint projects *inside* base segment
            proj_base = sorted([project(base[0]), project(base[1])])
            p0_proj = project(p0)
            p1_proj = project(p1)

            logger(f"    Projected p0: {p0_proj:.2f}")
            logger(f"    Projected p1: {p1_proj:.2f}")
            logger(f"    Base span: [{proj_base[0]:.2f}, {proj_base[1]:.2f}]")

            '''
            within_base = lambda t: proj_base[0] - projection_margin <= t <= proj_base[1] + projection_margin

            if within_base(p0_proj) or within_base(p1_proj):
                logger("    → Rejected: one or both endpoints project inside base segment.\n")
                continue
            '''
            logger("    → Accepted: segment is spatially aligned and extends line.\n")
            group.append(seg)
            to_remove.append(i)

            # Otherwise: reject segment if it lies fully inside projection span
            # i.e., overlapping or redundant
            continue

        logger("    → Rejected: segment is enclosed or overlapping.\n")
        for i in reversed(to_remove):
            del remaining[i]

        groups.append(group)

    return groups

def group_colinear_segments_ransac(segments, distance_thresh=5.0, angle_thresh_deg=2.0, min_inliers=4, max_trials=100, logger=print):
    import random
    if len(segments) < 2:
        logger("RANSAC skipped: not enough segments.")
        return []

    def compute_line_model(p0, p1):
        # Line: ax + by + c = 0
        dx, dy = p1 - p0
        a, b = -dy, dx
        norm = np.sqrt(a**2 + b**2)
        return a / norm, b / norm, -(a * p0[0] + b * p0[1]) / norm

    def point_to_line_dist(pt, line):
        a, b, c = line
        return abs(a * pt[0] + b * pt[1] + c)

    best_inliers = []
    best_model = None

    for _ in range(max_trials):
        s1, s2 = random.sample(segments, 2)
        p0 = (s1[0] + s1[1]) / 2
        p1 = (s2[0] + s2[1]) / 2
        if np.linalg.norm(p1 - p0) < 1e-2:
            continue

        model = compute_line_model(p0, p1)
        inliers = []

        for seg in segments:
            mid = (seg[0] + seg[1]) / 2
            dist = point_to_line_dist(mid, model)
            angle = compute_angle_deg(seg)
            model_angle = compute_angle_deg([p0, p1])
            if dist < distance_thresh and abs(angle - model_angle) < angle_thresh_deg:
                inliers.append(seg)

        if len(inliers) > len(best_inliers):
            best_inliers = inliers
            best_model = model

    if len(best_inliers) >= min_inliers:
        logger(f"RANSAC selected {len(best_inliers)} inliers.")
        return [best_inliers]
    else:
        logger("RANSAC failed to find a strong model.")
        return []

def cluster_group_positions(groups, orientation='horizontal', cluster_thresh=28, min_group_separation=15):
    axis = 0 if orientation == 'horizontal' else 1
    group_positions = []

    for group in groups:
        coords = [pt[axis] for seg in group for pt in seg]
        avg = sum(coords) / len(coords)
        group_positions.append(avg)

    sorted_indices = sorted(range(len(groups)), key=lambda i: group_positions[i])
    clusters = []
    i = 0

    while i < len(sorted_indices):
        curr = sorted_indices[i]
        pos_curr = group_positions[curr]

        if i + 1 < len(sorted_indices):
            next_ = sorted_indices[i + 1]
            pos_next = group_positions[next_]
            dist = abs(pos_next - pos_curr)

            if 0 <= dist <= cluster_thresh:
                clusters.append([curr, next_])
                i += 2
                continue

        # Either too close or no pair → single cluster
        clusters.append([curr])
        i += 1

    return clusters, group_positions


def select_best_cluster(clusters, groups, verbose=False, logger=print):
    if not clusters:
        return []

    def cluster_score(cluster):
        num_groups = len(cluster)
        total_length = sum(
            np.linalg.norm(seg[0] - seg[1]) for idx in cluster for seg in groups[idx]
        )
        return (num_groups, total_length)

    scored_clusters = [(cluster, cluster_score(cluster)) for cluster in clusters]
    sorted_clusters = sorted(scored_clusters, key=lambda x: (-x[1][0], -x[1][1]))

    if verbose:
        for i, (cluster, (num_groups, total_length)) in enumerate(sorted_clusters):
            logger(f"\nCluster {i}: groups={cluster}, num_groups={num_groups}, total_length={total_length:.1f}")
            for idx in cluster:
                logger(f"  Group {idx}:")
                for seg in groups[idx]:
                    (y0, x0), (y1, x1) = seg
                    logger(f"    Segment: ({x0:.1f}, {y0:.1f}) -> ({x1:.1f}, {y1:.1f})")

    return sorted_clusters[0][0]  # Best cluster (list of group indices)


# ---------- Drawing ----------

def draw_segments(img, segments, color, thickness=1):
    img_out = img.copy()
    for (y0, x0), (y1, x1) in segments:
        pt1 = (int(round(x0)), int(round(y0)))
        pt2 = (int(round(x1)), int(round(y1)))
        cv2.line(img_out, pt1, pt2, color, thickness)
    return img_out

def draw_groups(img, groups, thickness=2):
    img_out = img.copy()
    for group in groups:
        color = tuple(np.random.randint(80, 255, 3).tolist())
        for (y0, x0), (y1, x1) in group:
            pt1 = (int(round(x0)), int(round(y0)))
            pt2 = (int(round(x1)), int(round(y1)))
            cv2.line(img_out, pt1, pt2, color, thickness)
    return img_out

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

    for i, group_indices in enumerate(clusters):
        pos_values = [positions[idx] for idx in group_indices]
        avg_pos = np.mean(pos_values)
        logger(f"  Cluster {i}:")
        logger(f"    - Group indices: {group_indices}")
        logger(f"    - Avg {label} position: {avg_pos:.1f}")
        logger(f"    - Position values: {[f'{p:.1f}' for p in pos_values]}")
