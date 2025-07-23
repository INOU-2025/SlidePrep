import os
import cv2
import torch
import argparse
import numpy as np
import matplotlib.pyplot as plt
import kornia.feature as KF
from collections import deque
from detect_utils import (
    preprocess_for_sold2,
    compute_angle_deg,
    segment_length,
    group_colinear_segments_by_midpoint_projection,
    group_colinear_segments_ransac,
    print_colinear_groups,
    print_cluster_summary,
    cluster_group_positions,
    select_best_cluster,
    draw_segments,
    draw_groups,
    draw_clusters,
    draw_selected_cluster
)

VISUALIZATION_OPTIONS = [
    "original",
    "filtered",
    "grouped",
    "clustered",
    "best_clusters"
]

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


def is_image_file(filename):
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'))


def process_image(img_path, show=False, output_path=None, vis_mode="best_clusters", logger=print):
    img = cv2.imread(img_path)
    if img is None:
        logger(f"Error loading {img_path}")
        return

    pre_img = preprocess_for_sold2(img)
    model = KF.SOLD2(pretrained=True).eval()

    with torch.inference_mode():
        out = model(pre_img)

    segments = out['line_segments'][0].cpu().numpy()
    filtered = np.array([s for s in segments if segment_length(s) >= 50])

    angles = [compute_angle_deg(s) for s in filtered]
    logger(f"Angle stats: min={min(angles):.2f}, max={max(angles):.2f}, mean={np.mean(angles):.2f}")

    horiz = [s for s in filtered if 178 <= compute_angle_deg(s) <= 180 or 0 <= compute_angle_deg(s) <= 2]
    vert = [s for s in filtered if 91 <= compute_angle_deg(s) <= 92]

    logger(f"Total segments: {len(segments)}")
    logger(f"Filtered (length >= 50): {len(filtered)}")
    logger(f"Candidate horizontals (angle-based): {len(horiz)}")
    logger(f"Candidate verticals (angle-based): {len(vert)}")

    logger(f"\nGrouping horizontal segments")
    groups_h = group_colinear_segments_by_midpoint_projection(horiz, distance_thresh=5, logger=logger)
    logger(f"\nGrouping vertical segments")
    groups_v = group_colinear_segments_by_midpoint_projection(vert, distance_thresh=5, logger=logger)


    logger(f"\nHorizontal groups:")
    print_colinear_groups(groups_h, orientation='horizontal', logger=logger)
    logger(f"\nVertical groups:")
    print_colinear_groups(groups_v, orientation='vertical', logger=logger)

    clusters_h, positions_h = cluster_group_positions(groups_h, orientation='horizontal', cluster_thresh=38)
    clusters_v, positions_v = cluster_group_positions(groups_v, orientation='vertical', cluster_thresh=38)

    logger(f"\nORIGINAL CLUSTERS:")
    print_cluster_summary(clusters_h, positions_h, 'horizontal', logger=logger)
    print_cluster_summary(clusters_v, positions_v, 'vertical', logger=logger)

    logger(f"\nFILTERED CLUSTERS:")
    logger(f"\nHorizontal:")

    def select_nonoverlapping_clusters(clusters, groups, positions, min_spacing=10):
        scored = sorted(
            [(cl, (len(cl), sum(segment_length(s) for idx in cl for s in groups[idx])), np.mean([positions[idx] for idx in cl]))
             for cl in clusters],
            key=lambda x: (-x[1][0], -x[1][1])
        )
        selected = []
        used_positions = []
        for cl, _, pos in scored:
            if all(abs(pos - upos) > min_spacing for upos in used_positions):
                selected.append(cl)
                used_positions.append(pos)
        return selected

    top_h_clusters = select_nonoverlapping_clusters(clusters_h, groups_h, positions_h, min_spacing=10)
    logger(f"\nVertical:")
    top_v_clusters = select_nonoverlapping_clusters(clusters_v, groups_v, positions_v, min_spacing=10)

    img_out = img.copy()
    if vis_mode == "original":
        img_out = draw_segments(img_out, segments, (0, 0, 255))
    elif vis_mode == "filtered":
        img_out = draw_segments(img_out, horiz, (0, 255, 0))
        img_out = draw_segments(img_out, vert, (255, 0, 0))
    elif vis_mode == "grouped":
        img_out = draw_groups(img_out, groups_h + groups_v)
    elif vis_mode == "clustered":
        img_out = draw_clusters(img_out, groups_h, clusters_h)
        img_out = draw_clusters(img_out, groups_v, clusters_v)
    elif vis_mode == "best_clusters":
        for cl in top_h_clusters:
            img_out = draw_selected_cluster(img_out, groups_h, cl)
        for cl in top_v_clusters:
            img_out = draw_selected_cluster(img_out, groups_v, cl)
    else:
        raise ValueError(f"Invalid vis_mode: {vis_mode}")

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

        logger = Logger(filepath=log_path, enable=True)
        process_image(input_path, show=False, output_path=output_path, vis_mode=vis_mode, logger=logger)
        logger.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=str, help='Path to single image')
    parser.add_argument('--folder', type=str, help='Path to folder of images')
    parser.add_argument('--out', type=str, help='Output image or folder')
    parser.add_argument('--vis', type=str, choices=VISUALIZATION_OPTIONS, default='best_clusters')
    parser.add_argument('--suffix', type=str, default='_ch00.jpg', help='Only process files ending with this suffix')
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    if args.image:
        logger = Logger(enable=True)
        process_image(args.image, show=args.show, output_path=args.out if args.out else None, vis_mode=args.vis, logger=logger)
        logger.close()
    elif args.folder:
        if not args.out:
            raise ValueError("For batch mode, --out is required")
        batch_process(args.folder, args.out, args.vis, args.suffix)
    else:
        raise ValueError("You must provide either --image or --folder")
