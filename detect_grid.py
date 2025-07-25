import os
import cv2
import torch
import argparse
import numpy as np
import matplotlib.pyplot as plt
import kornia.feature as KF
from detect_utils import (
    preprocess_for_sold2,
    compute_angle_deg,
    segment_length,
    group_approximately_collinear_segments,
    print_colinear_groups,
    draw_groups,
    draw_clusters,
    identify_thick_line_groups,
    print_cluster_summary
)

MIN_SEGMENT_LENGTH = 50

VISUALIZATION_FUNCTIONS = {
    "original": lambda img, segments_h, segments_v, groups_h, groups_v, clusters_h, clusters_v: cv2.polylines(img.copy(), [np.int32(s.reshape(-1, 2)[:, ::-1]) for s in np.concatenate((segments_h, segments_v), axis=0)], False, (0, 0, 255), 1),
    "filtered": lambda img, segments_h, segments_v, groups_h, groups_v, clusters_h, clusters_v: cv2.polylines(cv2.polylines(img.copy(), [np.int32(s.reshape(-1, 2)[:, ::-1]) for s in segments_h], False, (0, 255, 0), 1), [np.int32(s.reshape(-1, 2)[:, ::-1]) for s in segments_v], False, (255, 0, 0), 1),
    "grouped": lambda img, segments_h, segments_v, groups_h, groups_v, clusters_h, clusters_v: draw_groups(img.copy(), groups_h + groups_v),
    "clustered": lambda img, segments_h, segments_v, groups_h, groups_v, clusters_h, clusters_v: draw_clusters(draw_clusters(img.copy(), clusters_h), clusters_v)
}

class Logger:
    def __init__(self, filepath=None, enable=True):
        self.file = open(filepath, 'w') if filepath else None
        self.enable = enable

    def __call__(self, msg):
        if not self.enable:
            return
        if self.file:
            self.file.write(str(msg) + '\n')
        else:
            print(msg)

    def close(self):
        if self.file:
            self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def is_image_file(filename):
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'))


def filter_and_group_segments(segments, logger):
    filtered = np.array([s for s in segments if segment_length(s) >= MIN_SEGMENT_LENGTH])

    angles = [compute_angle_deg(s) for s in filtered]
    logger(f"Angle stats: min={min(angles):.2f}, max={max(angles):.2f}, mean={np.mean(angles):.2f}")

    horiz = [s for s in filtered if 178 <= compute_angle_deg(s) <= 180 or 0 <= compute_angle_deg(s) <= 2]
    vert = [s for s in filtered if 91 <= compute_angle_deg(s) <= 92]

    logger(f"Filtered (length >= {MIN_SEGMENT_LENGTH}): {len(filtered)}")
    logger(f"Candidate horizontals (angle-based): {len(horiz)}")
    logger(f"Candidate verticals (angle-based): {len(vert)}")

    logger(f"\nGrouping horizontal segments")
    groups_h = group_approximately_collinear_segments(horiz)
    logger(f"\nGrouping vertical segments")
    groups_v = group_approximately_collinear_segments(vert)

    logger(f"\nHorizontal groups:")
    print_colinear_groups(groups_h, orientation='horizontal', logger=logger)
    logger(f"\nVertical groups:")
    print_colinear_groups(groups_v, orientation='vertical', logger=logger)

    return horiz, vert, groups_h, groups_v


def identify_clusters(groups_h, groups_v, logger):
    clusters_h = identify_thick_line_groups(groups_h)
    clusters_v = identify_thick_line_groups(groups_v)

    logger(f"\nCLUSTERS:")
    logger(f"\nHorizontal:")
    print_cluster_summary(clusters_h, 'horizontal', logger=logger)
    logger(f"\nVertical:")
    print_cluster_summary(clusters_v, 'vertical', logger=logger)

    return clusters_h, clusters_v


def render_visualization(img, vis_mode, segments, horiz, vert, groups_h, groups_v, clusters_h, clusters_v):
    if vis_mode not in VISUALIZATION_FUNCTIONS:
        raise ValueError(f"Invalid vis_mode: {vis_mode}")

    return VISUALIZATION_FUNCTIONS[vis_mode](img, horiz, vert, groups_h, groups_v, clusters_h, clusters_v)


def process_image(img_path, show=False, output_path=None, vis_mode="clustered", logger=print):
    img = cv2.imread(img_path)
    if img is None:
        logger(f"Error loading {img_path}")
        return

    pre_img = preprocess_for_sold2(img)
    model = KF.SOLD2(pretrained=True).eval()

    with torch.inference_mode():
        out = model(pre_img)

    segments = out['line_segments'][0].cpu().numpy()
    logger(f"Total segments: {len(segments)}")

    horiz, vert, groups_h, groups_v = filter_and_group_segments(segments, logger)
    clusters_h, clusters_v = identify_clusters(groups_h, groups_v, logger)

    img_out = render_visualization(img, vis_mode, segments, horiz, vert, groups_h, groups_v, clusters_h, clusters_v)

    if output_path:
        cv2.imwrite(output_path, img_out)
    if show:
        plt.imshow(cv2.cvtColor(img_out, cv2.COLOR_BGR2RGB))
        plt.axis('off')
        plt.title(vis_mode)
        plt.show()


def batch_process(folder_path, output_folder, vis_mode, suffix):
    os.makedirs(output_folder, exist_ok=True)
    log_folder = os.path.join(output_folder, "logs")
    os.makedirs(log_folder, exist_ok=True)

    for fname in sorted(os.listdir(folder_path)):
        if not (is_image_file(fname) and fname.endswith(suffix)):
            continue
        input_path = os.path.join(folder_path, fname)
        output_path = os.path.join(output_folder, fname)
        log_path = os.path.join(log_folder, os.path.splitext(fname)[0] + ".log")

        with Logger(filepath=log_path, enable=True) as logger:
            process_image(input_path, show=False, output_path=output_path, vis_mode=vis_mode, logger=logger)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=str, help='Path to single image')
    parser.add_argument('--folder', type=str, help='Path to folder of images')
    parser.add_argument('--out', type=str, help='Output image or folder')
    parser.add_argument('--vis', type=str, choices=list(VISUALIZATION_FUNCTIONS.keys()), default='clustered')
    parser.add_argument('--suffix', type=str, default='_ch00.jpg', help='Only process files ending with this suffix')
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    if args.image:
        with Logger(enable=True) as logger:
            process_image(args.image, show=args.show, output_path=args.out if args.out else None, vis_mode=args.vis, logger=logger)
    elif args.folder:
        if not args.out:
            raise ValueError("For batch mode, --out is required")
        batch_process(args.folder, args.out, args.vis, args.suffix)
    else:
        raise ValueError("You must provide either --image or --folder")
