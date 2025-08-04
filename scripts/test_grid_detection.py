from utils.debug.grid_detection_drawer import GridDetectionDrawer
from scripts.module_test_runner import StepTestRunner
from steps.grid_detection import GridDetectionStep
import argparse
import sys
from pathlib import Path

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main(config_path: str):
    grid_drawer = GridDetectionDrawer()
    runner = StepTestRunner(config_path, grid_drawer)

    step = GridDetectionStep(
        config=runner.cfg.grid_detection_config,
        debugger=runner.debugger,
        logger=runner.logger
    )

    runner.run_on_directory(
        step=step
    )

    runner.logger.info("Grid detection testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test grid detection on images")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)
