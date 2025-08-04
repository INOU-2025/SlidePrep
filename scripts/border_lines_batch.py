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

def contour_in_strict_border_zone(contour, shape, border_thickness, orientation):
    h, w = shape
    xs = contour[:, 0, 0]
    ys = contour[:, 0, 1]
    if orientation == 'horizontal':
        return all(y < border_thickness for y in ys) or all(y >= h - border_thickness for y in ys)
    elif orientation == 'vertical':
        return all(x < border_thickness for x in xs) or all(x >= w - border_thickness for x in xs)
    return False

def classify_contour(contour):
    rect = cv2.minAreaRect(contour)
    _, (w, h), angle = rect
    if w < h:
        angle = angle + 90
    angle = abs(angle)
    if abs(angle - 0) <= 2:
        return 'horizontal'
    elif abs(angle - 90) <= 2:
        return 'vertical'
    else:
        return 'other'

def draw_classified_contours(base_image, contours, template_shape, orientation, border_thickness):
    result = base_image.copy()
    if len(result.shape) == 2 or result.shape[2] == 1:
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
    h, w = result.shape[:2]
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

        is_valid = contour_fully_within_zone(box, (h, w), border_thickness, orientation)

        color = (0, 255, 0) if orientation == 'vertical' else (255, 0, 0)
        if not is_valid:
            color = (0, 0, 255)  # red

        cv2.drawContours(result, [box], 0, color, 2)
    return result

def contour_fully_within_zone(box, img_shape, border_thickness, orientation):
    h, w = img_shape
    if orientation == 'horizontal':
        in_top = all(y < border_thickness for _, y in box)
        in_bottom = all(y >= h - border_thickness for _, y in box)
        return in_top or in_bottom
    elif orientation == 'vertical':
        in_left = all(x < border_thickness for x, _ in box)
        in_right = all(x >= w - border_thickness for x, _ in box)
        return in_left or in_right
    return False


def draw_border_overlay(image, border_thickness):
    h, w = image.shape[:2]
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, border_thickness), (0, 0, 255), -1)
    cv2.rectangle(overlay, (0, h - border_thickness), (w, h), (0, 0, 255), -1)
    cv2.rectangle(overlay, (0, 0), (border_thickness, h), (0, 0, 255), -1)
    cv2.rectangle(overlay, (w - border_thickness, 0), (w, h), (0, 0, 255), -1)
    return cv2.addWeighted(overlay, 0.25, image, 0.75, 0)

'''
general case // template_length=300, thickness=20
thick border lines // template_length=100, thickness=7, border_thickness=35 
thin border lines // template_length=30, thickness=7, border_thickness=20
'''

def process_image(image_path, output_path, threshold=0.1, template_length=100, thickness=7, angles=[+2, -2], border_thickness=35):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"Could not read {image_path}")
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

    contours_h, _ = cv2.findContours(mask_h, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_v, _ = cv2.findContours(mask_v, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    base = draw_border_overlay(base, border_thickness)
    base = draw_classified_contours(base, contours_h, h_templates[0].shape, 'horizontal', border_thickness)
    base = draw_classified_contours(base, contours_v, v_templates[0].shape, 'vertical', border_thickness)

    cv2.imwrite(output_path, base)

def process_batch(input_folder, output_folder, ext="png"):
    os.makedirs(output_folder, exist_ok=True)
    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    for image_path in image_paths:
        filename = os.path.basename(image_path)
        output_path = os.path.join(output_folder, filename)
        print(f"Processing {filename}")
        process_image(image_path, output_path)
