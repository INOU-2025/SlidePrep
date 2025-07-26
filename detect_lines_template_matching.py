import cv2
import numpy as np
import os
from glob import glob

def create_line_template(length=60, thickness=20, angle_deg=2.0, orientation='horizontal'):
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

def compute_min_required_ratio(area, base_area=3000, base_ratio=0.95, alpha=0.157):
    ratio = base_ratio - alpha * np.log10(area / base_area)
    return max(0.0, min(1.0, ratio))  # Clamp between 0 and 1

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
            rect = cv2.minAreaRect(cnt)
            area = int(rect[1][0] * rect[1][1])
            box = cv2.boxPoints(rect)
            box = np.intp(box + offset - [pad_x, pad_y])

            # Draw rotated box (yellow) and axis-aligned box (green)
            '''
            cv2.drawContours(overlay, [box], 0, (255, 255, 0), 4)
            x, y, w, h = cv2.boundingRect(box)
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 1)
            '''

            # Dark pixel ratio on original image (not inverted!)
            mask_region = np.zeros_like(gray, dtype=np.uint8)
            cv2.fillPoly(mask_region, [box], 1)

            black_pixels = np.sum((gray == 0) & (mask_region == 1))
            total_pixels = np.sum(mask_region == 1)

            if total_pixels == 0:
                continue

            dark_ratio = black_pixels / total_pixels
            # print(f"[INFO] {key} box {i}: dark_ratio = {dark_ratio:.3f}")

            '''
            if dark_ratio < 0.9:
                cv2.drawContours(overlay, [box], 0, (255, 0, 0), 2)  # Rejected: blue
            else:
                cv2.drawContours(overlay, [box], 0, (0, 0, 255), 2)  # Accepted: red
            '''
            min_required_ratio = compute_min_required_ratio(area)

            if dark_ratio < min_required_ratio:
                print(f"[REJECT] dark_ratio={dark_ratio:.3f} < {min_required_ratio:.3f}")
                cv2.drawContours(overlay, [box], 0, (255, 0, 0), 2)
            else:
                print(f"[ACCEPT] dark_ratio={dark_ratio:.3f} ≥ {min_required_ratio:.3f}")
                cv2.drawContours(overlay, [box], 0, (0, 0, 255), 2)
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
