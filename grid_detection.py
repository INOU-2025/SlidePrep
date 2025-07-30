import cv2
import numpy as np
import os
import time
from glob import glob
from typing import Dict, Tuple

from config.config_schema import GridDetectionConfig
from utils.detection.line_template_factory import LineTemplateFactory
from utils.detection.grid_detection_drawer import GridDetectionDrawer
from core.app_config_manager import AppConfigManager
from core.logger import Logger
from core.debugger import Debugger

def initialize_environment(config_path: str):
    cfg = AppConfigManager.get_instance()
    cfg.initialize(config_path)

    logger = Logger.get_instance()
    logger.initialize(cfg.logging_config, enabled=cfg.logger_active)

    debugger = Debugger.get_instance()
    debugger.initialize(cfg.debug_config)

    return cfg, logger, debugger

def compute_min_required_ratio(area: float) -> float:
    if area >= 9500:
        return 0.85
    if area <= 2000:
        return 0.96
    return 0.96 - 0.11 * ((area - 2000) / 7500)

def border_touch_ratio(rotated_box: np.ndarray, orientation: str, shape: Tuple[int, int], margin: int) -> Tuple[int, float]:
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

def draw_and_analyze_contour(
    cnt, gray, key, offset, thresholds, drawer, fname, margin, logger
) -> Tuple[int, int, int]:
    cnt += offset
    area = cv2.contourArea(cnt)
    if area == 0:
        return 0, 0, 0

    rotated_rect = cv2.minAreaRect(cnt)
    rotated_box = cv2.boxPoints(rotated_rect).astype(np.intp)
    drawer.draw_box(rotated_box, color=(0, 255, 255), thickness=1)

    mask = np.zeros_like(gray, dtype=np.uint8)
    cv2.fillPoly(mask, [rotated_box], 1)
    dark_ratio = np.count_nonzero((gray == 0) & (mask == 1)) / max(np.count_nonzero(mask), 1)

    contour_mask = np.zeros_like(gray, dtype=np.uint8)
    cv2.drawContours(contour_mask, [cnt], -1, 1, -1)
    contour_dark_ratio = np.count_nonzero((gray == 0) & (contour_mask == 1)) / max(np.count_nonzero(contour_mask), 1)

    min_ratio = compute_min_required_ratio(area)
    (_, _), (w, h), raw_angle = rotated_rect
    angle = raw_angle + 90 if w < h else raw_angle
    angle = ((angle + 180) % 180) - 90
    length = max(w, h)
    angle_valid = (-4 <= angle <= 4) or (86 <= abs(angle) <= 94)

    accepted, maybe, decision = False, False, "REJECT"
    touches, ratio = -1, -1.0  # <- Initialize early

    if dark_ratio >= 0.93:
        accepted, decision = True, "ACCEPT (high confidence)"
    elif dark_ratio < 0.73:
        decision = "REJECT (low confidence)"
    else:
        maybe = True
        decision = "MAYBE (edge case)"
        if length >= thresholds['length']:
            accepted, maybe, decision = True, False, "ACCEPT (length override)"
        elif not angle_valid:
            maybe, decision = False, "REJECT (angle out of bounds)"

    if maybe:
        maybe = False
        touches, ratio = border_touch_ratio(rotated_box, key, gray.shape, margin)
        if contour_dark_ratio > 0.96 and dark_ratio >= 0.83:
            accepted, decision = True, "ACCEPT (contour ratio override)"
        elif contour_dark_ratio < 0.85 and dark_ratio < 0.80:
            decision = "REJECT (contour ratio override)"
        elif contour_dark_ratio >= 0.80 and dark_ratio >= 0.70 and touches and ratio > 0.9:
            accepted, decision = True, "ACCEPT (relaxed contour-touch override)"
        else:
            # TODO. This is a fallback decision. We need to revisit this logic. Perhaps some detections might be marked as maybe to be reviewed later further.
            accepted, decision = False, "REJECT (not enough evidences)"

    drawer.draw_contour(cnt, accepted=accepted, maybe=maybe)
    logger.debug(
        f"{fname},{area:.1f},{dark_ratio:.3f},{contour_dark_ratio:.3f},{min_ratio:.3f},"
        f"{length:.1f},{key},{angle:.2f},{decision},{int(touches)},{ratio:.2f}"
    )

    return int(accepted), int(not accepted and not maybe), int(maybe)

def process_image(path: str, templates: Dict[str, np.ndarray], gd: GridDetectionConfig, logger, debugger):
    fname = os.path.basename(path)
    logger.info(f"Processing image: {fname}")
    gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        logger.error(f"Cannot read {fname}")
        return

    inverted = cv2.bitwise_not(gray)
    drawer = debugger.create_drawer(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
    thresholds = {
        "horizontal": gd.horizontal_area_threshold,
        "vertical": gd.vertical_area_threshold,
        "length": 0.55 * max(gray.shape)
    }

    stats = {"accept": 0, "reject": 0, "maybe": 0}
    for key, tmpl in templates.items():
        t_h, t_w = tmpl.shape
        pad = (t_h // 2, t_w // 2)
        padded = cv2.copyMakeBorder(inverted, *pad, *pad[::-1], cv2.BORDER_CONSTANT, value=0)
        result = cv2.matchTemplate(padded, tmpl, cv2.TM_SQDIFF_NORMED)
        mask = (result < np.percentile(result, gd.percentile_thresh)).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            if cv2.contourArea(cnt) >= thresholds[key]:
                a, r, m = draw_and_analyze_contour(
                    cnt, gray, key, np.array([t_w // 2, t_h // 2]) - [pad[1], pad[0]],
                    thresholds, drawer, fname, gd.margin, logger
                )
                stats["accept"] += a
                stats["reject"] += r
                stats["maybe"] += m

    drawer.save(fname)
    logger.info(
        f"Processed {fname}. Accept: {stats['accept']}, Reject: {stats['reject']}, Maybe: {stats['maybe']}"
    )

def batch_process(input_dir: str, gd: GridDetectionConfig, logger, debugger):
    images = glob(os.path.join(input_dir, "*.png"))
    logger.info(f"Found {len(images)} images in {input_dir}")
    factory = LineTemplateFactory(length=gd.line_length, thickness=gd.line_thickness, angle_deg=gd.angle_deg)
    templates = {"horizontal": factory.create("horizontal"), "vertical": factory.create("vertical")}
    start = time.time()
    for path in images:
        try:
            process_image(path, templates, gd, logger, debugger)
        except Exception:
            logger.exception(f"Error processing {path}")
    logger.info(f"Batch completed in {time.time() - start:.2f}s")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", default="config/init_config.json")
    args = parser.parse_args()

    cfg, logger, debugger = initialize_environment(args.config)
    batch_process(args.input, cfg.grid_detection_config, logger, debugger)