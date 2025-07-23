import cv2
import numpy as np
import math
import argparse
from pathlib import Path

def generate_mask(image_path, output_path):
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Could not read image: {image_path}")
        return
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50,
                            minLineLength=gray.shape[1] // 4,
                            maxLineGap=10)

    def angle_between_lines(line):
        x1, y1, x2, y2 = line
        return math.atan2(y2 - y1, x2 - x1)

    perpendicular_pairs = []
    if lines is not None:
        for i in range(len(lines)):
            for j in range(i+1, len(lines)):
                theta1 = angle_between_lines(lines[i][0])
                theta2 = angle_between_lines(lines[j][0])
                angle_diff = abs(theta1 - theta2)
                angle_diff = min(angle_diff, np.pi - angle_diff)
                if 0.95 * (np.pi/2) < angle_diff < 1.05 * (np.pi/2):
                    perpendicular_pairs.append((lines[i][0], lines[j][0]))

    mask = np.zeros_like(gray, dtype=np.uint8)
    if perpendicular_pairs:
        for line in perpendicular_pairs[0]:
            x1, y1, x2, y2 = line
            cv2.line(mask, (x1, y1), (x2, y2), 255, thickness=3)
    elif lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(mask, (x1, y1), (x2, y2), 255, thickness=3)

    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    cv2.imwrite(str(output_path), mask)

def process_images(input_path, output_dir):
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        out_file = output_dir / (input_path.stem + "_mask.png")
        generate_mask(input_path, out_file)
    else:
        for ext in ('*.jpg', '*.jpeg', '*.png', '*.tif', '*.tiff'):
            for img_file in input_path.glob(ext):
                out_file = output_dir / (img_file.stem + "_mask.png")
                generate_mask(img_file, out_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate mask for grid lines in images.")
    parser.add_argument("input", help="Path to an image file or folder")
    parser.add_argument("output", help="Directory for output mask images")
    args = parser.parse_args()
    process_images(args.input, args.output)
