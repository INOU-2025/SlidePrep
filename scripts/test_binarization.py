import argparse
import sys
from pathlib import Path

# Ensure project root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.test_runner import StepTestRunner
from src.steps import BinarizationStep


def main(config_path: str):
    runner = StepTestRunner(config_path)

    step = BinarizationStep(config=runner.cfg.binarization_config)

    runner.run_on_directory(step=step)

    runner.logger.info("Binarization testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test binarization on images")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)
