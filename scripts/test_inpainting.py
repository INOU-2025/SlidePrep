"""CLI script for testing the LaMa inpainting pipeline step."""

import argparse
import sys
from pathlib import Path

# Ensure project root is on the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.test_runner import StepTestRunner
from src.steps import InpaintingStep


def main(config_path: str) -> None:
    """Run the inpainting step on all images in the input directory."""
    runner = StepTestRunner(config_path)

    step = InpaintingStep(config=runner.cfg.inpainting_config)

    runner.run_on_directory(step=step)

    runner.logger.info("Inpainting testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test inpainting step")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)
