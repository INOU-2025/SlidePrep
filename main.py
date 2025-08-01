import os
import cv2
from glob import glob
from core import bootstrap, get_config, get_logger
from steps import BinarizationStep, GridDetectionStep
from utils import get_supported_image_patterns, filter_images_by_suffix
# Future: from steps.mask_creation import MaskCreationStep, etc.


def run_pipeline(config_path: str):
    """
    Run the complete image processing pipeline.
    
    Args:
        config_path: Path to the configuration file
    """
    try:
        # Bootstrap the application with all services
        bootstrap(config_path)
        
        # Get services from container
        cfg = get_config()
        logger = get_logger()
    except Exception as e:
        print(f"Failed to initialize application: {e}")
        return False

    # Get input folder and suffix filter from config
    input_folder = cfg.general_config.input_path
    suffix_filter = cfg.general_config.suffix_filter
    
    if not input_folder:
        logger.error("input_path must be specified in the general config section")
        return False
        
    if not os.path.exists(input_folder):
        logger.error(f"Input folder does not exist: {input_folder}")
        return False

    # Set up pipeline steps - binarization first, then grid detection
    try:
        steps = [
            BinarizationStep(cfg.binarization_config),
            GridDetectionStep(cfg.grid_detection_config),
            # Future: MaskCreationStep(...), etc.
        ]
        logger.info(f"Initialized {len(steps)} pipeline steps")
    except Exception as e:
        logger.error(f"Failed to initialize pipeline steps: {e}")
        return False

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
        else:
            # This executes only if the loop completed without breaking
            successful_count += 1
            logger.info(f"Successfully processed {fname}")

    logger.info(f"Pipeline completed. Processed {successful_count}/{len(images)} images successfully")
    return successful_count > 0

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="SlidePrep: Image processing pipeline for slide preparation"
    )
    parser.add_argument(
        "config", 
        nargs="?", 
        default="config/init_config.json", 
        help="Path to config file (default: config/init_config.json)"
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