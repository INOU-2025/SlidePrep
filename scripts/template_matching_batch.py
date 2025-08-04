
import cv2
import numpy as np
import os
from glob import glob

def generate_blurred_template(length, thickness, angle_deg, orientation):
    if orientation == 'horizontal':
        template = np.zeros((thickness, length), dtype=np.uint8)
        cv2.rectangle(template, (0, 0), (length-1, thickness-1), 255, -1)
    else:
        template = np.zeros((length, thickness), dtype=np.uint8)
        cv2.rectangle(template, (0, 0), (thickness-1, length-1), 255, -1)
    template = cv2.GaussianBlur(template, (5, 5), 0)
    if angle_deg != 0:
        center = (template.shape[1] // 2, template.shape[0] // 2)
        M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
        template = cv2.warpAffine(template, M, (template.shape[1], template.shape[0]), flags=cv2.INTER_LINEAR, borderValue=0)
    return template

def pad_response(response, target_shape):
    pad_y = target_shape[0] - response.shape[0]
    pad_x = target_shape[1] - response.shape[1]
    return cv2.copyMakeBorder(response, 0, pad_y, 0, pad_x, cv2.BORDER_CONSTANT, value=1.0)

def draw_corrected_rects(image, mask, template_shape, color):
    overlay = cv2.cvtColor(image.copy(), cv2.COLOR_GRAY2BGR)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    offset_x = template_shape[1] // 2
    offset_y = template_shape[0] // 2
    for cnt in contours:
        if cv2.contourArea(cnt) < 100:
            continue
        rect = cv2.minAreaRect(cnt)
        center, size, angle = rect
        corrected_center = (center[0] + offset_x, center[1] + offset_y)
        corrected_rect = (corrected_center, size, angle)
        box = cv2.boxPoints(corrected_rect)
        box = np.intp(box)
        cv2.drawContours(overlay, [box], 0, color, 2)
    return overlay

def process_image(path, out_dir, threshold=0.1, template_length=300, thickness=20, angles=[+2, -2]):
    name = os.path.splitext(os.path.basename(path))[0]
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"Could not read {path}")
        return

    inverted = cv2.bitwise_not(image)

    h_templates = [generate_blurred_template(template_length, thickness, a, 'horizontal') for a in angles]
    v_templates = [generate_blurred_template(template_length, thickness, a, 'vertical') for a in angles]

    h_responses = [pad_response(cv2.matchTemplate(inverted, tpl, cv2.TM_SQDIFF_NORMED), image.shape) for tpl in h_templates]
    v_responses = [pad_response(cv2.matchTemplate(inverted, tpl, cv2.TM_SQDIFF_NORMED), image.shape) for tpl in v_templates]

    h_map = np.minimum.reduce(h_responses)
    v_map = np.minimum.reduce(v_responses)

    mask_h = (h_map < threshold).astype(np.uint8) * 255
    mask_v = (v_map < threshold).astype(np.uint8) * 255

    rects_h = draw_corrected_rects(image, mask_h, h_templates[0].shape, (0, 0, 255))
    rects_v = draw_corrected_rects(image, mask_v, v_templates[0].shape, (0, 255, 0))

    os.makedirs(out_dir, exist_ok=True)
    cv2.imwrite(os.path.join(out_dir, f"{name}_mask_h.png"), mask_h)
    cv2.imwrite(os.path.join(out_dir, f"{name}_mask_v.png"), mask_v)
    cv2.imwrite(os.path.join(out_dir, f"{name}_rects_h.png"), rects_h)
    cv2.imwrite(os.path.join(out_dir, f"{name}_rects_v.png"), rects_v)

def process_batch(folder, out_dir):
    paths = glob(os.path.join(folder, "*.png"))
    for path in paths:
        print(f"Processing {path}")
        process_image(path, out_dir)

# USAGE EXAMPLE:
# process_batch("input_images", "output_results")
