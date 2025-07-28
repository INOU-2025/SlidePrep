import cv2
import numpy as np
import os
import time
from glob import glob
from typing import Dict, Tuple, Any
from utils.detection.line_template_factory import LineTemplateFactory
from utils.detection.grid_detection_config import GridDetectionConfig
from utils.detection.grid_detection_drawer import GridDetectionDrawer
import logging

# Load configuration
config: GridDetectionConfig = GridDetectionConfig("config/grid_detection.json")
log: logging.Logger = config.logger

ANGLE_DEG: float = config.angle_deg
MARGIN: int = config.margin
PERCENTILE_THRESH: int = config.percentile_thresh
HORIZONTAL_AREA_THRESHOLD: int = config.horizontal_area_threshold
VERTICAL_AREA_THRESHOLD: int = config.vertical_area_threshold
LINE_LENGTH: int = config.line_length
LINE_THICKNESS: int = config.line_thickness

def compute_min_required_ratio(area: float) -> float:
    if area >= 9500:
        base_ratio =  0.85
    elif area <= 2000:
        base_ratio = 0.96
    else:
        base_ratio = 0.96 - 0.11 * ((area - 2000) / 7500)
    return base_ratio

def is_edge_aligned(
    box: np.ndarray, 
    key: str, 
    image_shape: Tuple[int, int], 
    margin: int = MARGIN
) -> bool:
    img_h, img_w = image_shape
    box_x = box[:, 0]
    box_y = box[:, 1]
    near_left   = np.any(box_x < margin)
    near_right  = np.any(box_x > img_w - margin)
    near_top    = np.any(box_y < margin)
    near_bottom = np.any(box_y > img_h - margin)
    return (
        (key == "vertical" and (near_left or near_right)) or
        (key == "horizontal" and (near_top or near_bottom))
    )

def border_touch_ratio(
    rotated_box: np.ndarray, 
    orientation: str, 
    image_shape: Tuple[int, int], 
    margin: int = MARGIN
) -> Tuple[int, float]:
    h, w = image_shape
    box = np.array(rotated_box, dtype=np.float32)
    rect = cv2.minAreaRect(box)
    pts = cv2.boxPoints(rect)
    edges = [(pts[i], pts[(i + 1) % 4]) for i in range(4)]
    edge_lengths = [np.linalg.norm(p1 - p2) for p1, p2 in edges]
    long_edges = sorted([(i, l) for i, l in enumerate(edge_lengths)], key=lambda x: -x[1])[:2]
    total_length = long_edges[0][1]
    max_overlap = 0.0
    num_samples = 0
    for i, _ in long_edges:
        p1, p2 = edges[i]
        num_samples = int(np.linalg.norm(p1 - p2))
        if num_samples == 0:
            continue
        xs = np.linspace(p1[0], p2[0], num_samples)
        ys = np.linspace(p1[1], p2[1], num_samples)
        if orientation == "horizontal":
            near_top = np.abs(ys) < margin
            near_bottom = np.abs(ys - h) < margin
            match = near_top | near_bottom
        elif orientation == "vertical":
            near_left = np.abs(xs) < margin
            near_right = np.abs(xs - w) < margin
            match = near_left | near_right
        else:
            continue
        overlap_length = np.sum(match)
        if overlap_length > max_overlap:
            max_overlap = overlap_length
    ratio = max_overlap / num_samples if num_samples > 0 else 0.0
    touches = int(ratio > 0)
    return touches, ratio

def log_detection(
    fname: str, 
    area: float, 
    dark_ratio: float, 
    contour_dark_ratio: float, 
    min_required_ratio: float,
    length: float, 
    orientation_type: str, 
    angle: float, 
    decision: str, 
    touches_margin: int, 
    touch_ratio: float
) -> None:
    log_msg = (
        f"{fname},{area:.1f},{dark_ratio:.3f},{contour_dark_ratio:.3f},{min_required_ratio:.3f},"
        f"{length:.1f},{orientation_type},{angle:.2f},{decision},{int(touches_margin)},{touch_ratio:.2f}"
    )
    log.debug(log_msg)

def process_image(
    image_path: str, 
    output_path: str, 
    templates: Dict[str, np.ndarray], 
    percentile_thresh: int = PERCENTILE_THRESH
) -> None:
    start_time = time.time()
    log.info(f"Processing image: {image_path}")
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        log.error(f"Cannot read {image_path}")
        return
    inverted = cv2.bitwise_not(gray)
    overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    drawer = GridDetectionDrawer(overlay, enabled=config.visualization_enabled)
    area_thresholds = {
        "horizontal": HORIZONTAL_AREA_THRESHOLD,
        "vertical": VERTICAL_AREA_THRESHOLD
    }
    fname = os.path.basename(image_path)

    n_accept, n_reject, n_maybe = 0, 0, 0

    for key, tmpl in templates.items():
        t_h, t_w = tmpl.shape
        offset = np.array([t_w // 2, t_h // 2])
        pad_y, pad_x = t_h // 2, t_w // 2
        padded = cv2.copyMakeBorder(inverted, pad_y, pad_y, pad_x, pad_x, cv2.BORDER_CONSTANT, value=0)
        result = cv2.matchTemplate(padded, tmpl, cv2.TM_SQDIFF_NORMED)
        threshold = np.percentile(result, percentile_thresh)
        mask = (result < threshold).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for i, cnt in enumerate(contours):
            if cv2.contourArea(cnt) < area_thresholds[key]:
                continue

            cnt = cnt + offset - [pad_x, pad_y]  # Shift contour
            area = cv2.contourArea(cnt)
            if area == 0:
                continue
            box = cv2.approxPolyDP(cnt, epsilon=1.0, closed=True).reshape(-1, 2)

            debug_rect = cv2.minAreaRect(cnt)
            debug_box = cv2.boxPoints(debug_rect)
            debug_box = np.intp(debug_box)
            drawer.draw_box(debug_box, color=(0, 255, 255), thickness=1)

            rotated_rect = cv2.minAreaRect(cnt)
            rotated_box = cv2.boxPoints(rotated_rect).astype(np.intp)

            mask_region = np.zeros_like(gray, dtype=np.uint8)
            cv2.fillPoly(mask_region, [rotated_box], 1)

            rotated_mask = np.zeros_like(gray, dtype=np.uint8)
            cv2.fillPoly(rotated_mask, [rotated_box], 1)
            rotated_black_pixels = np.sum((gray == 0) & (rotated_mask == 1))
            rotated_total_pixels = np.sum(rotated_mask == 1)
            if rotated_total_pixels == 0:
                continue
            dark_ratio = rotated_black_pixels / rotated_total_pixels

            contour_mask = np.zeros_like(gray, dtype=np.uint8)
            cv2.drawContours(contour_mask, [cnt], -1, 1, thickness=-1)
            contour_black_pixels = np.sum((gray == 0) & (contour_mask == 1))
            contour_total_pixels = np.sum(contour_mask == 1)
            if contour_total_pixels == 0:
                continue
            contour_dark_ratio = contour_black_pixels / contour_total_pixels

            min_required_ratio = compute_min_required_ratio(area)

            rotated_rect = cv2.minAreaRect(cnt)
            (_, _), (w, h), raw_angle = rotated_rect
            angle = raw_angle + 90 if w < h else raw_angle

            if angle > 90:
                angle -= 180
            elif angle < -90:
                angle += 180

            angle_valid = (
                    (-4 <= angle <= 4) or
                    (86 <= abs(angle) <= 94)
            )

            length = max(w, h)
            orientation_type = key
            touches_margin, touch_ratio = -1, -1

            if dark_ratio >= 0.93:
                decision = "ACCEPT (high confidence)"
                accepted = True
                maybe = False
                n_accept += 1
            elif dark_ratio < 0.73:
                decision = "REJECT (low confidence)"
                accepted = False
                maybe = False
                n_reject += 1
            else:
                decision = "MAYBE (edge case)"
                maybe = True
                n_maybe += 1
                min_required_ratio = compute_min_required_ratio(area)
                accepted = False
                img_h, img_w = gray.shape
                length_threshold = 0.55 * (img_w if key == "horizontal" else img_h)

                if not accepted and length >= length_threshold:
                    accepted = True
                    maybe = False
                    decision = "ACCEPT (length override)"
                    n_accept += 1
                    n_maybe -= 1  # Remove from maybe count if overridden

                angle_valid = (
                        (-4 <= angle <= 4) or
                        (86 <= abs(angle) <= 94)
                )

                if maybe and not angle_valid:
                    maybe = False
                    accepted = False
                    decision = "REJECT (angle out of bounds)"
                    n_reject += 1
                    n_maybe -= 1  # Remove from maybe count if overridden

            if maybe:
                touches_margin, touch_ratio = border_touch_ratio(rotated_box, orientation_type, gray.shape)
                if contour_dark_ratio > 0.96 and dark_ratio >= 0.83:
                    accepted = True
                    maybe = False
                    decision = "ACCEPT (contour ratio override)"
                    n_accept += 1
                    n_maybe -= 1
                elif contour_dark_ratio < 0.85 and dark_ratio < 0.80:
                    accepted = False
                    maybe = False
                    decision = "REJECT (contour ratio override)"
                    n_reject += 1
                    n_maybe -= 1
                elif (
                        contour_dark_ratio >= 0.80 and
                        dark_ratio >= 0.70 and
                        touches_margin == 1 and
                        touch_ratio > 0.9
                ):
                    accepted = True
                    maybe = False
                    decision = "ACCEPT (relaxed contour-touch override)"
                    n_accept += 1
                    n_maybe -= 1
                else:
                    accepted = False
                    decision = "REJECT (not enough evidences to accept segment)"
                    n_reject += 1
                    n_maybe -= 1

            drawer.draw_contour(box, accepted=accepted, maybe=maybe)

            # Log detection result
            log_detection(
                fname, area, dark_ratio, contour_dark_ratio, min_required_ratio,
                length, orientation_type, angle, decision, touches_margin, touch_ratio
            )

    fname = os.path.basename(image_path)
    out_path = os.path.join(output_path, fname)
    drawer.save(out_path)
    elapsed = time.time() - start_time
    log.info(f"Saved output: {out_path}")
    log.info(f"Image processed in {elapsed:.2f} seconds. Accepted: {n_accept}, Rejected: {n_reject}, Maybe: {n_maybe}")

def batch_process(input_dir: str) -> None:
    output_dir: str = config.debug_output_dir
    os.makedirs(output_dir, exist_ok=True)
    images: list[str] = glob(os.path.join(input_dir, "*.png"))
    log.info(f"Found {len(images)} images in {input_dir}")
    factory: LineTemplateFactory = LineTemplateFactory(length=LINE_LENGTH, thickness=LINE_THICKNESS, angle_deg=ANGLE_DEG)
    templates: Dict[str, np.ndarray] = {
        "horizontal": factory.create(orientation='horizontal'),
        "vertical": factory.create(orientation='vertical')
    }
    total_accept: int = 0
    total_reject: int = 0
    total_maybe: int = 0
    start_time: float = time.time()
    for img_path in images:
        try:
            process_image(img_path, output_dir, templates)
        except Exception as e:
            log.exception(f"Exception occurred while processing {img_path}")
    elapsed: float = time.time() - start_time
    log.info(f"Batch processing completed in {elapsed:.2f} seconds for {len(images)} images.")

if __name__ == "__main__":
    import argparse
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input folder with PNG images")
    args: argparse.Namespace = parser.parse_args()
    batch_process(args.input)
