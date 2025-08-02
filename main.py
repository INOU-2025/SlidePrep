import os
import cv2
from glob import glob
from core import bootstrap, get_config, get_logger
from core.pipeline import Pipeline
from steps import BinarizationStep, GridDetectionStep
from utils import get_supported_image_patterns, filter_images_by_suffix


def run_pipeline(config_path: str):
    """
    Run the complete image processing pipeline.
    
    This is the main production pipeline that processes images through configured steps:
    1. Bootstrap initializes all services via dependency injection
    2. Each step is instantiated with its specific configuration
    3. Steps validate input and return processed results consistently
    4. No drawer is attached for production runs (debug mode disabled)
    
    Args:
        config_path: Path to the configuration file
    """
    try:
        bootstrap(config_path)
        
        cfg = get_config()
        logger = get_logger()
    except Exception as e:
        print(f"Failed to initialize application: {e}")
        return False

    input_folder = cfg.general_config.input_path
    suffix_filter = cfg.general_config.suffix_filter

    if not input_folder:
        logger.error(
            "input_path must be specified in the general config section")
        return False

    if not os.path.exists(input_folder):
        logger.error(f"Input folder does not exist: {input_folder}")
        return False

    try:
        steps = [
            BinarizationStep(cfg.binarization_config),
            GridDetectionStep(cfg.grid_detection_config),
        ]
        pipeline = Pipeline(steps)
        logger.info(f"Initialized {len(steps)} pipeline steps")
    except Exception as e:
        logger.error(f"Failed to initialize pipeline steps: {e}")
        return False

    image_extensions = get_supported_image_patterns()
    images = []
    for ext in image_extensions:
        images.extend(glob(os.path.join(input_folder, ext)))
        images.extend(glob(os.path.join(input_folder, ext.upper())))

    images = filter_images_by_suffix(images, suffix_filter)
    if suffix_filter:
        logger.info(f"Suffix filter '{suffix_filter}' applied")

    if not images:
        logger.warning(f"No images found in {input_folder}")
        return False

    logger.info(f"Found {len(images)} images to process in {input_folder}")

    successful_count = 0
    for image_path in images:
        fname = os.path.basename(image_path)
        logger.info(f"Processing {fname}")
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            logger.error(f"Could not read {fname}")
            continue

        result = pipeline.run(gray)
        if result is not None:
            successful_count += 1
            logger.info(f"Successfully processed {fname}")

    logger.info(
        f"Pipeline completed. Processed {successful_count}/{len(images)} images successfully")
    return successful_count > 0


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="SlidePrep: Image processing pipeline for slide preparation"
    )
    parser.add_argument(
        "config",
        help="Path to config file"
    )
    args = parser.parse_args()

    try:
        success = run_pipeline(args.config)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
