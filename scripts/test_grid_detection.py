import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from steps.grid_detection import GridDetectionStep
from scripts.module_test_runner import StepTestRunner


def main(config_path: str):
    # Initialize test runner
    runner = StepTestRunner(config_path)
    
    # Create grid detection step
    step = GridDetectionStep(config=runner.cfg.grid_detection_config)
    
    # Process all images in the configured input directory
    # This will automatically load images, run the step, and save results
    runner.run_on_directory(step, output_suffix="grid_detected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test grid detection on images")
    parser.add_argument("config", nargs="?", default="config/test/grid_detection_test_config.json", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)