import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from steps.binarization import BinarizationStep
from scripts.module_test_runner import StepTestRunner


def main(config_path: str):
    # Initialize test runner without drawer (plain image saving for binarization)
    runner = StepTestRunner(config_path)  # No drawer = plain images
    
    # Create binarization step
    step = BinarizationStep(
        config=runner.cfg.binarization_config,
        debugger=runner.debugger,
        logger=runner.logger
    )
    
    # Run the step on all images - debugger will save plain binarized images
    runner.run_on_directory(step, "binarized")
    
    runner.logger.info("Binarization testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test binarization on images")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)
