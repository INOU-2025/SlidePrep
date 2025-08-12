import argparse
import sys
from pathlib import Path

# Add project root to Python path FIRST
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Now import project modules
from src.utils.debug.detection_drawer import DetectionDrawer
from src.scripts.test_runner import StepTestRunner
from src.steps import GridDetectionStep
from src.utils.debug.detection_result_writer import DetectionResultWriter


def main(config_path: str):
    adaptive_drawer = DetectionDrawer()
    detection_writer = DetectionResultWriter()
    
    runner = StepTestRunner(config_path, adaptive_drawer, detection_writer)

    step = GridDetectionStep(
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