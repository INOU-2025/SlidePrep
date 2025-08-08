import os
import cv2
from glob import glob
from core import bootstrap, get_config, get_logger, Container
from core.context import PipelineContext
from core.pipeline import Pipeline
from steps import BinarizationStep, GridDetectionStep, GridRefinementStep
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
        context = PipelineContext()
        Container.register_singleton("pipeline_context", context)
    except Exception as e:
        print(f"Failed to initialize application: {e}")
        return False

    input_folder = cfg.general_config.input_path
    suffix_filter = cfg.general_config.suffix_filter

    if not input_folder:
        logger.critical(
            "input_path must be specified in the general config section")
        return False

    if not os.path.exists(input_folder):
        logger.critical(f"Input folder does not exist: {input_folder}")
        return False

    try:
        steps = [
            BinarizationStep(cfg.binarization_config),
            GridDetectionStep(cfg.grid_detection_config),
            GridRefinementStep(cfg.grid_refinement_config),
        ]
        pipeline = Pipeline(steps)
        logger.info(f"Pipeline initialized with {len(steps)} steps")
    except Exception as e:
        logger.critical(f"Failed to initialize pipeline steps: {e}")
        return False

    image_extensions = get_supported_image_patterns()
    images = []
    for ext in image_extensions:
        images.extend(glob(os.path.join(input_folder, ext)))
        images.extend(glob(os.path.join(input_folder, ext.upper())))

    images = filter_images_by_suffix(images, suffix_filter)
    if suffix_filter:
        logger.debug(f"Applied suffix filter '{suffix_filter}', found {len(images)} matching images")

    if not images:
        logger.warning(f"No images found in {input_folder}")
        return False

    logger.info(f"Starting batch processing of {len(images)} images")

    successful_count = 0
    for image_path in images:
        fname = os.path.basename(image_path)
        context.current_image_path = image_path
        logger.debug(f"Loading image: {fname}")
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            logger.error(f"Could not read {fname}")
            continue

        result = pipeline.run(gray)
        if result is not None:
            successful_count += 1
            logger.debug(f"Successfully processed {fname}")

    logger.info(
        f"Batch processing completed: {successful_count}/{len(images)} images processed successfully")
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
