import argparse
import sys
from pathlib import Path

# Add project root to Python path FIRST
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now import project modules
from utils.debug.adaptive_detection_drawer import AdaptiveDetectionDrawer
from scripts.module_test_runner import StepTestRunner
from steps.adaptive_grid_detection import AdaptiveGridDetectionStep


def main(config_path: str):
    adaptive_drawer = AdaptiveDetectionDrawer()
    runner = StepTestRunner(config_path, adaptive_drawer)

    step = AdaptiveGridDetectionStep(
        config=runner.cfg.grid_detection_config,
        debugger=runner.debugger,
        logger=runner.logger
    )

    runner.run_on_directory(
        step=step
    )

    runner.logger.info("Adaptive grid detection testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test adaptive grid detection on images")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)