import os
import cv2
import numpy as np
from glob import glob
import argparse

# ---------- PARAMETERS ----------
adaptive_block_size = 51
adaptive_C = 2
min_size = 300
clahe_clip = 2.0
clahe_tile = (8, 8)
morph_kernel_size = 3

# ---------- PROCESSING FUNCTION ----------
def process_image(image_path, output_path, invert=False):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"[WARNING] Skipping {image_path} (cannot read)")
        return

    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=clahe_tile)
    enhanced = clahe.apply(img)

    mask = cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        adaptive_block_size,
        adaptive_C
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size))
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned)
    final_mask = np.zeros_like(cleaned)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= min_size:
            final_mask[labels == i] = 255

    if invert:
        final_mask = cv2.bitwise_not(final_mask)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, final_mask)
    print(f"[INFO] Saved: {output_path}")

# ---------- CLI ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tissue segmentation using adaptive thresholding and CLAHE.")
    parser.add_argument('--image', type=str, help='Path to a single image')
    parser.add_argument('--folder', type=str, help='Path to a folder of images')
    parser.add_argument('--out', type=str, required=True, help='Output file (for --image) or output folder (for --folder)')
    parser.add_argument('--suffix', type=str, default='_ch00.jpg', help='Only process files ending with this suffix (batch mode only)')
    parser.add_argument('--invert', action='store_true', help='Invert the final mask (useful for some applications)')
    args = parser.parse_args()

    if args.image and args.folder:
        raise ValueError("Specify only one of --image or --folder.")
    elif not args.image and not args.folder:
        raise ValueError("You must specify either --image or --folder.")

    if args.image:
        if not os.path.isfile(args.image):
            raise FileNotFoundError(f"Image file not found: {args.image}")
        out_path = args.out
        if os.path.isdir(out_path):
            fname = os.path.basename(args.image)
            name, _ = os.path.splitext(fname)
            out_path = os.path.join(out_path, f"{name}_mask.png")
        process_image(args.image, out_path, invert=args.invert)

    elif args.folder:
        if not os.path.isdir(args.folder):
            raise NotADirectoryError(f"Folder not found: {args.folder}")
        os.makedirs(args.out, exist_ok=True)
        image_paths = [f for f in glob(os.path.join(args.folder, '*')) if f.endswith(args.suffix)]
        for path in image_paths:
            fname = os.path.basename(path)
            name, _ = os.path.splitext(fname)
            out_path = os.path.join(args.out, f"{name}_mask.png")
            process_image(path, out_path, invert=args.invert)
