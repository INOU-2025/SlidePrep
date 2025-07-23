import cv2
import numpy as np
import argparse
from pathlib import Path

def remove_grid_lines_simple(image_path):
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binary mask for dark lines
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Detect horizontal and vertical lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (img.shape[1] // 30, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, img.shape[0] // 30))

    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)
    mask = cv2.bitwise_or(horizontal, vertical)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)

    # Inpaint
    cleaned = cv2.inpaint(img, mask, 3, cv2.INPAINT_NS)
    return cleaned

def process_images(input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        out_img = remove_grid_lines_simple(input_path)
        cv2.imwrite(str(output_path / input_path.name), out_img)
    else:
        for ext in ('*.jpg', '*.jpeg', '*.png', '*.tif', '*.tiff'):
            for img_file in input_path.glob(ext):
                try:
                    out_img = remove_grid_lines_simple(img_file)
                    cv2.imwrite(str(output_path / img_file.name), out_img)
                except Exception as e:
                    print(f"Failed to process {img_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove grid lines from microscopy images.")
    parser.add_argument("input", help="Path to an image file or folder")
    parser.add_argument("output", help="Directory for output images")
    args = parser.parse_args()

    process_images(args.input, args.output)