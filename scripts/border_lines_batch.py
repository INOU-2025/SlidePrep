import cv2
import numpy as np
import os
from glob import glob
from shapely.geometry import Polygon

def merge_similar_lines(lines, angle_threshold=np.deg2rad(2), rho_threshold=20):
    if lines is None:
        return []
    merged = []
    used = [False] * len(lines)
    for i in range(len(lines)):
        if used[i]: continue
        rho1, theta1 = lines[i][0]
        group = [(rho1, theta1)]
        used[i] = True
        for j in range(i + 1, len(lines)):
            if used[j]: continue
            rho2, theta2 = lines[j][0]
            if abs(rho1 - rho2) < rho_threshold and abs(theta1 - theta2) < angle_threshold:
                group.append((rho2, theta2))
                used[j] = True
        avg_rho = np.mean([g[0] for g in group])
        avg_theta = np.mean([g[1] for g in group])
        merged.append((avg_rho, avg_theta))
    return merged

def compute_line_intersections(rho, theta, width, height):
    a, b = np.cos(theta), np.sin(theta)
    if abs(b) < 1e-6: b = 1e-6
    points = []
    for y in [0, height - 1]:
        x = (rho - y * b) / a if abs(a) > 1e-6 else None
        if x is not None and 0 <= x <= width - 1:
            points.append((int(round(x)), y))
    for x in [0, width - 1]:
        y = (rho - x * a) / b if abs(b) > 1e-6 else None
        if y is not None and 0 <= y <= height - 1:
            points.append((x, int(round(y))))
    unique_points = []
    for pt in points:
        if pt not in unique_points:
            unique_points.append(pt)
        if len(unique_points) == 2:
            break
    return unique_points if len(unique_points) == 2 else None

def classify_line(theta_deg, threshold=2):
    if abs(theta_deg - 90) <= threshold:
        return 'horizontal'
    elif abs(theta_deg - 0) <= threshold or abs(theta_deg - 180) <= threshold:
        return 'vertical'
    else:
        return 'other'

def horizontal_line_strict(pts, height, border_thickness):
    return all(y < border_thickness or y >= height - border_thickness for _, y in pts)

def vertical_line_strict(pts, width, border_thickness):
    return all(x < border_thickness or x >= width - border_thickness for x, _ in pts)

def create_border_polygon(pts, orientation, w, h):
    if orientation == 'horizontal':
        y0, y1 = pts[0][1], pts[1][1]
        y_closest = 0 if y0 < h // 2 and y1 < h // 2 else h
        polygon = Polygon([pts[0], pts[1], (pts[1][0], y_closest), (pts[0][0], y_closest)])
    elif orientation == 'vertical':
        x0, x1 = pts[0][0], pts[1][0]
        x_closest = 0 if x0 < w // 2 and x1 < w // 2 else w
        polygon = Polygon([pts[0], pts[1], (x_closest, pts[1][1]), (x_closest, pts[0][1])])
    else:
        return None
    return polygon

def process_image(image_path, annotate=True):
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    h, w = gray.shape
    border_thickness = 70
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=150)
    merged_lines = merge_similar_lines(lines)
    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    for rho, theta in merged_lines:
        pts = compute_line_intersections(rho, theta, w, h)
        if not pts:
            continue

        theta_deg = np.rad2deg(theta)
        category = classify_line(theta_deg)

        is_valid = False
        if category == 'horizontal' and horizontal_line_strict(pts, h, border_thickness):
            color = (0, 255, 0)  # green
            is_valid = True
        elif category == 'vertical' and vertical_line_strict(pts, w, border_thickness):
            color = (255, 0, 0)  # blue
            is_valid = True
        else:
            color = (0, 0, 255)  # red

        cv2.line(vis, pts[0], pts[1], color, 2)

        if is_valid:
            polygon = create_border_polygon(pts, category, w, h)
            if polygon and polygon.is_valid:
                poly_pts = np.array(polygon.exterior.coords, dtype=np.int32)
                overlay = vis.copy()
                cv2.fillPoly(overlay, [poly_pts], color)
                cv2.addWeighted(overlay, 0.3, vis, 0.7, 0, vis)

        if annotate:
            label = f"{pts[0]} → {pts[1]}"
            mid_x = (pts[0][0] + pts[1][0]) // 2
            mid_y = (pts[0][1] + pts[1][1]) // 2
            cv2.putText(vis, label, (mid_x + 10, mid_y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (255, 255, 255), 1, cv2.LINE_AA)

    # Draw border zones (semi-transparent red overlay)
    overlay_zone = vis.copy()
    cv2.rectangle(overlay_zone, (0, 0), (w, border_thickness), (0, 0, 255), -1)
    cv2.rectangle(overlay_zone, (0, h - border_thickness), (w, h), (0, 0, 255), -1)
    cv2.rectangle(overlay_zone, (0, 0), (border_thickness, h), (0, 0, 255), -1)
    cv2.rectangle(overlay_zone, (w - border_thickness, 0), (w, h), (0, 0, 255), -1)
    cv2.addWeighted(overlay_zone, 0.25, vis, 0.75, 0, vis)

    return vis

def process_batch(input_folder, output_folder, ext="png", annotate=True):
    os.makedirs(output_folder, exist_ok=True)
    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    for path in image_paths:
        filename = os.path.basename(path)
        output_path = os.path.join(output_folder, filename)
        vis = process_image(path, annotate=annotate)
        cv2.imwrite(output_path, vis)
