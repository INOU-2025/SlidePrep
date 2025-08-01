import argparse
import os
import cv2

from core.context import PipelineContext
from core.logger import Logger
from core.debugger import Debugger
from core.app_config_manager import AppConfigManager
from steps.grid_detection import GridDetectionStep
from utils.image_utils import get_supported_image_formats


def load_grayscale_contexts(input_folder: str, suffix_filter: str = None) -> list[PipelineContext]:
    contexts = []
    supported_formats = get_supported_image_formats()
    for fname in sorted(os.listdir(input_folder)):
        if not fname.lower().endswith(supported_formats):
            continue
        
        # Apply suffix filter if specified (on filename without extension)
        if suffix_filter:
            name_without_ext = os.path.splitext(fname)[0]
            if not name_without_ext.endswith(suffix_filter):
                continue
            
        path = os.path.join(input_folder, fname)
        gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        ctx = PipelineContext()
        ctx.image_name = fname
        ctx.gray_image = gray
        contexts.append(ctx)
    return contexts


def main(config_path: str):
    # Initialize global config, logger, and debugger
    cfg = AppConfigManager.get_instance()
    cfg.initialize(config_path)

    logger = Logger.get_instance()
    logger.initialize(cfg.log_config, enabled=cfg.logger_active, output_dir=cfg.debug_config.output_dir)

    debugger = Debugger.get_instance()
    debugger.initialize(cfg.debug_config, cfg.debug_active)

    # Set up the pipeline step with logger and debugger
    step = GridDetectionStep(config=cfg.grid_detection_config, logger=logger, debugger=debugger)

    # Load and run using config values
    if not cfg.general_config.input_path:
        logger.error("input_path must be specified in the general config section")
        return
    
    contexts = load_grayscale_contexts(cfg.general_config.input_path, cfg.general_config.suffix_filter)
    logger.info(f"Loaded {len(contexts)} images from {cfg.general_config.input_path}")

    for ctx in contexts:
        try:
            step.run(ctx)
        except Exception as e:
            logger.exception(f"Failed to process {ctx.image_name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", default="config/test/grid_detection_test_config.json", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)