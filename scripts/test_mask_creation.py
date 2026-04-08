from src.steps import MaskCreationStep
from scripts.test_runner import StepTestRunner
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(config_path: str) -> None:
    runner = StepTestRunner(config_path)

    step = MaskCreationStep()

    runner.run_on_directory(step=step)

    runner.logger.info("Mask creation testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test mask creation step")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)
