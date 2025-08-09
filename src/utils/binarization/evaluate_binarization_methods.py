from glob import glob
from utils.image_utils import get_supported_image_patterns, filter_images_by_suffix
from steps.binarization import BinarizationStep
from core.bootstrap import bootstrap, get_config, get_logger, get_debugger
import argparse
import numpy as np
import os
import cv2
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def evaluate_binarization_methods(config_path: str):
    """Evaluate different binarization methods on all images in a folder."""

    # Bootstrap the application with all services
    bootstrap(config_path)

    # Get services from container
    cfg = get_config()
    logger = get_logger()

    # Get input folder from config
    input_folder = cfg.general_config.input_path
    suffix_filter = cfg.general_config.suffix_filter

    if not input_folder:
        logger.error(
            "input_path must be specified in the general config section")
        return

    if not os.path.exists(input_folder):
        logger.error(f"Input folder not found: {input_folder}")
        return

    # Get all supported images from the folder
    image_extensions = get_supported_image_patterns()
    images = []
    for ext in image_extensions:
        images.extend(glob(os.path.join(input_folder, ext)))
        images.extend(glob(os.path.join(input_folder, ext.upper())))

    # Apply suffix filter if specified
    images = filter_images_by_suffix(images, suffix_filter)
    if suffix_filter:
        logger.info(f"Applied suffix filter: '{suffix_filter}'")

    if not images:
        if suffix_filter:
            logger.error(
                f"No images found with suffix '{suffix_filter}' in {input_folder}")
        else:
            logger.error(f"No supported images found in {input_folder}")
        logger.error(f"Supported formats: {', '.join(image_extensions)}")
        return

    logger.info(f"Found {len(images)} images to process in {input_folder}")

    # Get output directory from debug config
    output_base_dir = cfg.debug_config.output_dir

    if not output_base_dir:
        logger.error("debug_config.output_dir must be specified in config")
        return

    logger.info(f"Output will be saved to: {output_base_dir}")

    # Test the current production method
    methods = [
        {
            "name": "Combined Differential (Production)",
            "config": {
                "threshold_method": "combined_differential"
            }
        }
    ]

    # Create output directories for each method
    method_dirs = {}
    for method in methods:
        method_safe_name = method['name'].replace(
            " ", "_").replace("(", "").replace(")", "").lower()
        method_dir = os.path.join(output_base_dir, method_safe_name)
        os.makedirs(method_dir, exist_ok=True)
        method_dirs[method_safe_name] = method_dir
        logger.info(f"Created output directory: {method_dir}")

    # Statistics tracking
    total_processed = 0
    method_stats = {method['name']: {'success': 0,
                                     'failed': 0, 'files': []} for method in methods}

    # Process each image
    for image_path in images:
        fname = os.path.basename(image_path)
        base_name = os.path.splitext(fname)[0]

        # Load the image
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            logger.warning(f"Could not load image: {fname}")
            continue

        logger.info(f"\nProcessing {fname} ({gray.shape[1]}x{gray.shape[0]})")
        total_processed += 1

        # Test each method on this image
        for method in methods:
            method_name = method['name']
            method_safe_name = method_name.replace(
                " ", "_").replace("(", "").replace(")", "").lower()

            try:
                # Create config from method settings
                from config.config_schema import BinarizationConfig
                config = BinarizationConfig(**method['config'])

                # Create step (services injected via container)
                step = BinarizationStep(config)

                # Run binarization directly on image data
                result_image = step.run(gray.copy())

                if result_image is not None:
                    # Save the binarized result
                    output_filename = f"{base_name}_binarized.png"
                    output_path = os.path.join(
                        method_dirs[method_safe_name], output_filename)

                    cv2.imwrite(output_path, result_image)

                    # Update statistics
                    method_stats[method_name]['success'] += 1
                    method_stats[method_name]['files'].append(output_path)

                    # Calculate pixel statistics
                    white_pixels = np.sum(result_image == 255)
                    total_pixels = result_image.size
                    white_percent = 100 * white_pixels / total_pixels

                    logger.info(
                        f"  ✓ {method_name}: {white_percent:.1f}% white pixels → {output_path}")
                else:
                    method_stats[method_name]['failed'] += 1
                    logger.warning(
                        f"  ✗ {method_name}: Failed to create binary image")

            except Exception as e:
                method_stats[method_name]['failed'] += 1
                logger.error(f"  ✗ {method_name}: Error - {e}")

    # Print final summary
    logger.info(f"\n{'='*60}")
    logger.info(f"BATCH PROCESSING SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Input folder: {input_folder}")
    logger.info(f"Output folder: {output_base_dir}")
    logger.info(f"Images processed: {total_processed}")
    logger.info(f"")

    for method_name, stats in method_stats.items():
        method_safe_name = method_name.replace(
            " ", "_").replace("(", "").replace(")", "").lower()
        success_rate = (stats['success'] / total_processed *
                        100) if total_processed > 0 else 0
        logger.info(f"{method_name}:")
        logger.info(
            f"  Success: {stats['success']}/{total_processed} ({success_rate:.1f}%)")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Output folder: {method_dirs[method_safe_name]}")
        logger.info(f"  Files generated: {len(stats['files'])}")
        logger.info(f"")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate binarization methods on a batch of images")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    evaluate_binarization_methods(args.config)
