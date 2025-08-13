import os
import cv2
from glob import glob
from typing import Any, Optional

from src.core import bootstrap, get_config, get_logger, get_pipeline_context
from src.core.pipeline import Pipeline
from src.steps import (
    BinarizationStep,
    GridDetectionStep,
    GridRefinementStep,
    MaskCreationStep,
    InpaintingStep,
    ImgConversionStep,
)
from src.utils import get_supported_image_patterns, filter_images_by_suffix


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
        context = get_pipeline_context()
        cfg = get_config()
        logger = get_logger()

    except Exception as e:
        print(f"Failed to initialize application: {e}")
        return False

    input_folder = cfg.general_config.input_path
    output_folder = cfg.general_config.output_path
    output_suffix = cfg.general_config.output_suffix
    suffix_filter = cfg.general_config.suffix_filter

    if not input_folder:
        logger.critical(
            "input_path must be specified in the general config section")
        return False

    if not os.path.exists(input_folder):
        logger.critical(f"Input folder does not exist: {input_folder}")
        return False

    os.makedirs(output_folder, exist_ok=True)

    try:
        steps = [
            BinarizationStep(config=cfg.binarization_config),
            GridDetectionStep(config=cfg.grid_detection_config),
            GridRefinementStep(cfg.grid_refinement_config),
            MaskCreationStep(),
            InpaintingStep(config=cfg.inpainting_config),
            ImgConversionStep(config=cfg.img_conversion_config),
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
        logger.debug(
            f"Applied suffix filter '{suffix_filter}', "
            f"found {len(images)} matching images",
        )

    if not images:
        logger.warning(f"No images found in {input_folder}")
        return False

    logger.info(f"Starting batch processing of {len(images)} images")

    successful_count = 0
    for image_path in images:
        fname = os.path.basename(image_path)
        logger.debug(f"Loading image: {fname}")
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            logger.error(f"Could not read {fname}")
            continue

        # Update context with the current image path. Image shape was
        # determined during bootstrapping and does not need to be reset.
        context.input_image_path = image_path

        result = pipeline.run(gray)
        if result is None:
            logger.error(f"Processing failed for {fname}")
            continue

        output_image: Any = result
        metadata: Optional[dict[str, Any]] = None
        if isinstance(result, tuple):
            output_image, metadata = result

        if output_image.ndim == 3 and output_image.shape[2] == 3:
            output_image = cv2.cvtColor(output_image, cv2.COLOR_RGB2BGR)

        name, ext = os.path.splitext(fname)
        if metadata and "format" in metadata:
            ext = f".{metadata['format']}"
        out_name = f"{name}{output_suffix}{ext}"
        out_path = os.path.join(output_folder, out_name)
        if not cv2.imwrite(out_path, output_image):
            logger.error(f"Failed to save result for {fname}")
            continue

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
