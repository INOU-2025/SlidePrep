import os
import cv2
from glob import glob
from core.app_config_manager import AppConfigManager
from core.logger import Logger
from core.debugger import Debugger
from core.context import PipelineContext
from steps.binarization import BinarizationStep
from steps.grid_detection import GridDetectionStep
from utils.image_utils import get_supported_image_patterns, filter_images_by_suffix
# Future: from steps.mask_creation import MaskCreationStep, etc.

def initialize_environment(config_path: str):
    cfg = AppConfigManager.get_instance()
    cfg.initialize(config_path)

    logger = Logger.get_instance()
    logger.initialize(cfg.logging_config, enabled=cfg.logger_active)

    debugger = Debugger.get_instance()
    debugger.initialize(cfg.debug_config)

    return cfg, logger, debugger

def run_pipeline(input_folder: str, config_path: str, suffix_filter: str = None):
    cfg, logger, debugger = initialize_environment(config_path)

    # Set up pipeline steps - binarization first, then grid detection
    steps = [
        BinarizationStep(cfg.binarization_config, logger=logger, debugger=debugger),
        GridDetectionStep(cfg.grid_detection_config, logger=logger, debugger=debugger),
        # Future: MaskCreationStep(...), etc.
    ]

    # Support common image formats
    image_extensions = get_supported_image_patterns()
    images = []
    for ext in image_extensions:
        images.extend(glob(os.path.join(input_folder, ext)))
        images.extend(glob(os.path.join(input_folder, ext.upper())))  # Also check uppercase extensions
    
    # Apply suffix filter if specified
    images = filter_images_by_suffix(images, suffix_filter)
    if suffix_filter:
        logger.info(f"Suffix filter '{suffix_filter}' applied")
    
    logger.info(f"Found {len(images)} images to process in {input_folder}")

    for image_path in images:
        fname = os.path.basename(image_path)
        logger.info(f"Processing {fname}")
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            logger.error(f"Could not read {fname}")
            continue

        ctx = PipelineContext(
            input_image=gray,
            image_path=image_path, 
            image_name=fname,
            gray_image=gray
        )

        for step in steps:
            try:
                step.run(ctx)
            except Exception as e:
                logger.exception(f"Error in step {step.name} for {fname}: {e}")
                break

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input folder with image files (supports PNG, JPG, JPEG, TIF, TIFF, BMP, WEBP)")
    parser.add_argument("--config", default="config/init_config.json", help="Path to config file")
    parser.add_argument("--suffix", help="Only process files where the filename (without extension) ends with this suffix (e.g., '_ch00', '_processed')")
    args = parser.parse_args()

    run_pipeline(args.input, args.config, args.suffix)