import os
import cv2
from glob import glob
from core.bootstrap import bootstrap, get_config, get_logger
from steps.binarization import BinarizationStep
from steps.grid_detection import GridDetectionStep
from utils.image_utils import get_supported_image_patterns, filter_images_by_suffix
# Future: from steps.mask_creation import MaskCreationStep, etc.


def run_pipeline(config_path: str):
    # Bootstrap the application with all services
    bootstrap(config_path)
    
    # Get services from container
    cfg = get_config()
    logger = get_logger()

    # Get input folder and suffix filter from config
    input_folder = cfg.general_config.input_path
    suffix_filter = cfg.general_config.suffix_filter
    
    if not input_folder:
        logger.error("input_path must be specified in the general config section")
        return

    # Set up pipeline steps - binarization first, then grid detection
    steps = [
        BinarizationStep(cfg.binarization_config),
        GridDetectionStep(cfg.grid_detection_config),
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

        # Use direct function chaining - each step takes input and returns output
        current_data = gray
        
        for step in steps:
            try:
                # Run step with current data (services injected via container)
                result = step.run(current_data)
                
                # Handle different return types
                if isinstance(result, tuple):
                    # For steps that return (image, metadata) like grid detection
                    current_data, metadata = result
                    logger.info(f"Step {step.name} completed with metadata: {metadata}")
                else:
                    # For steps that return just an image like binarization
                    current_data = result
                    logger.info(f"Step {step.name} completed")
                    
            except Exception as e:
                logger.exception(f"Error in step {step.name} for {fname}: {e}")
                break

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", default="config/init_config.json", help="Path to config file")
    args = parser.parse_args()

    run_pipeline(args.config)