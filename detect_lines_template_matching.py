import cv2
import numpy as np
import os
from glob import glob
from detect_utils import LineTemplateFactory

def compute_min_required_ratio(area, is_edge_case=False):
    if area >= 9500:
        base_ratio =  0.85
    elif area <= 2000:
        base_ratio = 0.96
    else:
        # Linear interpolation between 0.96 (at 2000) and 0.85 (at 9500)
        base_ratio = 0.96 - 0.11 * ((area - 2000) / 7500)
    return base_ratio


def is_edge_aligned(box, key, image_shape, margin=5):
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

def border_touch_ratio(rotated_box, orientation, image_shape, margin=5):
    h, w = image_shape
    box = np.array(rotated_box, dtype=np.float32)

    # Get long edges of box
    rect = cv2.minAreaRect(box)
    pts = cv2.boxPoints(rect)

    # Build edges and identify long ones
    edges = [(pts[i], pts[(i + 1) % 4]) for i in range(4)]
    edge_lengths = [np.linalg.norm(p1 - p2) for p1, p2 in edges]
    long_edges = sorted([(i, l) for i, l in enumerate(edge_lengths)], key=lambda x: -x[1])[:2]
    total_length = long_edges[0][1]

    max_overlap = 0.0
    for i, _ in long_edges:
        p1, p2 = edges[i]

        # Sample points along edge
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
    touches = ratio > 0
    return touches, ratio



def process_image(image_path, output_path, templates, percentile_thresh=2):
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        print(f"[ERROR] Cannot read {image_path}")
        return

    inverted = cv2.bitwise_not(gray)  # For template matching
    overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)  # For display/annotation

    area_thresholds = {
        "horizontal": 2000,
        "vertical": 2000
    }

    fname = os.path.basename(image_path)
    log_path = os.path.join(output_path, "detection_log.csv")
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("file,area,dark_ratio,contour_dark_ratio,min_required_ratio,length,orientation,angle,decision,touches_margin,touch_ratio\n")

    for key, tmpl in templates.items():
        t_h, t_w = tmpl.shape
        offset = np.array([t_w // 2, t_h // 2])
        pad_y, pad_x = t_h // 2, t_w // 2

        padded = cv2.copyMakeBorder(inverted, pad_y, pad_y, pad_x, pad_x, cv2.BORDER_CONSTANT, value=0)
        result = cv2.matchTemplate(padded, tmpl, cv2.TM_SQDIFF_NORMED)
        threshold = np.percentile(result, percentile_thresh)
        # print(f"[INFO] {key} template threshold = {threshold:.4f}")
        mask = (result < threshold).astype(np.uint8) * 255

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for i, cnt in enumerate(contours):
            if cv2.contourArea(cnt) < area_thresholds[key]:
                continue

            # print(f"[INFO] We process contour {i}")

            cnt = cnt + offset - [pad_x, pad_y]  # Shift contour
            area = cv2.contourArea(cnt)
            if area == 0:
                continue
            box = cv2.approxPolyDP(cnt, epsilon=1.0, closed=True).reshape(-1, 2)

            # Debug visualization
            debug_rect = cv2.minAreaRect(cnt)
            debug_box = cv2.boxPoints(debug_rect)
            debug_box = np.intp(debug_box)
            cv2.drawContours(overlay, [debug_box], 0, (0, 255, 255), 1)  # Yellow rectangle

            # Dark pixel ratio on original image (not inverted!)
            '''
            mask_region = np.zeros_like(gray, dtype=np.uint8)
            cv2.fillPoly(mask_region, [box], 1)

            black_pixels = np.sum((gray == 0) & (mask_region == 1))
            total_pixels = np.sum(mask_region == 1)
            '''

            rotated_rect = cv2.minAreaRect(cnt)
            rotated_box = cv2.boxPoints(rotated_rect).astype(np.intp)

            mask_region = np.zeros_like(gray, dtype=np.uint8)
            cv2.fillPoly(mask_region, [rotated_box], 1)

            # Rotated rectangle mask
            rotated_mask = np.zeros_like(gray, dtype=np.uint8)
            cv2.fillPoly(rotated_mask, [rotated_box], 1)
            rotated_black_pixels = np.sum((gray == 0) & (rotated_mask == 1))
            rotated_total_pixels = np.sum(rotated_mask == 1)
            if rotated_total_pixels == 0:
                continue
            dark_ratio = rotated_black_pixels / rotated_total_pixels

            # Contour mask
            contour_mask = np.zeros_like(gray, dtype=np.uint8)
            cv2.drawContours(contour_mask, [cnt], -1, 1, thickness=-1)
            contour_black_pixels = np.sum((gray == 0) & (contour_mask == 1))
            contour_total_pixels = np.sum(contour_mask == 1)
            if contour_total_pixels == 0:
                continue
            contour_dark_ratio = contour_black_pixels / contour_total_pixels

            is_edge_case = is_edge_aligned(box, key, gray.shape)
            min_required_ratio = compute_min_required_ratio(area, is_edge_case=is_edge_case)

            rotated_rect = cv2.minAreaRect(cnt)
            (_, _), (w, h), raw_angle = rotated_rect
            angle = raw_angle + 90 if w < h else raw_angle

            # Normalize to [-90, 90]
            if angle > 90:
                angle -= 180
            elif angle < -90:
                angle += 180

            angle_valid = (
                    (-4 <= angle <= 4) or  # Near 0°
                    (86 <= abs(angle) <= 94)  # Near ±90°
            )

            length = max(w, h)
            orientation_type = key  # Already 'horizontal' or 'vertical'
            touches_margin, touch_ratio = -1, -1

            if dark_ratio >= 0.93:
                decision = "ACCEPT (high confidence)"
                accepted = True
                maybe = False
            elif dark_ratio < 0.73:
                decision = "REJECT (low confidence)"
                accepted = False
                maybe = False
            else:
                decision = "MAYBE (edge case)"
                maybe = True
                min_required_ratio = compute_min_required_ratio(area, is_edge_case=is_edge_case)
                # accepted = dark_ratio >= min_required_ratio
                accepted = False
                img_h, img_w = gray.shape
                length_threshold = 0.55 * (img_w if key == "horizontal" else img_h)

                if not accepted and length >= length_threshold:
                    accepted = True
                    maybe = False
                    decision = "ACCEPT (length override)"

                angle_valid = (
                        (-4 <= angle <= 4) or  # Near 0°
                        (86 <= abs(angle) <= 94)  # Near ±90°
                )

                if maybe and not angle_valid:
                    maybe = False
                    accepted = False
                    decision = "REJECT (angle out of bounds)"

            # Additional override for maybe cases
            if maybe:

                touches_margin, touch_ratio = border_touch_ratio(rotated_box, orientation_type, gray.shape)

                if contour_dark_ratio > 0.96 and dark_ratio >= 0.83:
                    accepted = True
                    maybe = False
                    decision = "ACCEPT (contour ratio override)"
                elif contour_dark_ratio < 0.85 and dark_ratio < 0.80:
                    accepted = False
                    maybe = False
                    decision = "REJECT (contour ratio override)"

                elif (
                        contour_dark_ratio >= 0.80 and
                        dark_ratio >= 0.70 and
                        touches_margin == 1 and
                        touch_ratio > 0.9
                ):
                    accepted = True
                    maybe = False
                    decision = "ACCEPT (relaxed contour-touch override)"
                else:
                    accepted = False
                    decision = "REJECT (not enough evidences to accept segment)"

            if accepted:
                cv2.drawContours(overlay, [box], 0, (0, 0, 255), 2)
            elif maybe:
                cv2.drawContours(overlay, [box], 0, (0, 255, 0), 2)
            else:
                cv2.drawContours(overlay, [box], 0, (255, 0, 0), 2)


            # print(f"[{decision}] dark_ratio={dark_ratio:.3f} (threshold={min_required_ratio:.3f})")
            with open(log_path, "a") as f:
                f.write(
                    f"{fname},{area:.1f},{dark_ratio:.3f},{contour_dark_ratio:.3f},{min_required_ratio:.3f},{length:.1f},{orientation_type},{angle:.2f},{decision},{int(touches_margin)},{touch_ratio:.2f}\n")

    fname = os.path.basename(image_path)
    out_path = os.path.join(output_path, fname.replace('.png', '_detected.png'))
    cv2.imwrite(out_path, overlay)
    # print(f"[OK] Saved: {out_path}")

def batch_process(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    images = glob(os.path.join(input_dir, "*.png"))

    factory = LineTemplateFactory(angle_deg=2.0)
    templates = {
        "horizontal": factory.create(orientation='horizontal'),
        "vertical": factory.create(orientation='vertical')
    }

    for img_path in images:
        process_image(img_path, output_dir, templates)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input folder with PNG images")
    parser.add_argument("--output", required=True, help="Output folder to save annotated images")
    args = parser.parse_args()

    batch_process(args.input, args.output)
