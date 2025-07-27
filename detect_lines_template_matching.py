import cv2
import numpy as np
import os
from glob import glob

def create_line_template(length=60, thickness=21, angle_deg=2.0, orientation='horizontal'):
    size = (length + thickness, length + thickness)
    template = np.zeros(size, dtype=np.uint8)

    if orientation == 'horizontal':
        start = (thickness // 2, size[1] // 2 - thickness // 2)
        end = (size[0] - thickness // 2, size[1] // 2 + thickness // 2)
    elif orientation == 'vertical':
        start = (size[0] // 2 - thickness // 2, thickness // 2)
        end = (size[0] // 2 + thickness // 2, size[1] - thickness // 2)
    else:
        raise ValueError("orientation must be 'horizontal' or 'vertical'")

    cv2.rectangle(template, start, end, 255, -1)
    center = (size[0] // 2, size[1] // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    rotated = cv2.warpAffine(template, rot_mat, size, flags=cv2.INTER_LINEAR, borderValue=0)
    return rotated

def compute_min_required_ratio(area, is_edge_case=False):
    if area >= 9500:
        base_ratio =  0.85
    elif area <= 2000:
        base_ratio = 0.96
    else:
        # Linear interpolation between 0.96 (at 2000) and 0.85 (at 9500)
        base_ratio = 0.96 - 0.11 * ((area - 2000) / 7500)

    if is_edge_case:
        base_ratio *= 0.98  # apply 8% relaxation
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

def process_image(image_path, output_path, templates, percentile_thresh=1):
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
            f.write("file,area,dark_ratio,min_required_ratio\n")

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
            mask_region = np.zeros_like(gray, dtype=np.uint8)
            cv2.fillPoly(mask_region, [box], 1)

            black_pixels = np.sum((gray == 0) & (mask_region == 1))
            total_pixels = np.sum(mask_region == 1)

            if total_pixels == 0:
                continue

            dark_ratio = black_pixels / total_pixels
            # print(f"[INFO] {key} box {i}: dark_ratio = {dark_ratio:.3f}")

            is_edge_case = is_edge_aligned(box, key, gray.shape)

            min_required_ratio = compute_min_required_ratio(area, is_edge_case=is_edge_case)

            if dark_ratio < min_required_ratio:
                print(f"[REJECT] dark_ratio={dark_ratio:.3f} < {min_required_ratio:.3f}")
                cv2.drawContours(overlay, [box], 0, (255, 0, 0), 2)
            else:
                print(f"[ACCEPT] dark_ratio={dark_ratio:.3f} ≥ {min_required_ratio:.3f}")
                cv2.drawContours(overlay, [box], 0, (0, 0, 255), 2)

            print(
                f"[{key} box {i}: area={area:.1f}, dark_ratio={dark_ratio:.3f}, threshold={min_required_ratio:.3f}")
            with open(log_path, "a") as f:
                f.write(f"{fname},{area:.1f},{dark_ratio:.3f},{min_required_ratio:.3f}\n")

    fname = os.path.basename(image_path)
    out_path = os.path.join(output_path, fname.replace('.png', '_detected.png'))
    cv2.imwrite(out_path, overlay)
    # print(f"[OK] Saved: {out_path}")

def batch_process(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    images = glob(os.path.join(input_dir, "*.png"))

    templates = {
        "horizontal": create_line_template(angle_deg=2.0, orientation='horizontal'),
        "vertical": create_line_template(angle_deg=2.0, orientation='vertical')
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
