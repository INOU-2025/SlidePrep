from src.steps import ImgConversionStep
from scripts.test_runner import StepTestRunner
import argparse
import sys
from pathlib import Path

# Ensure project root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(config_path: str):
    runner = StepTestRunner(config_path)
    cfg = runner.cfg.img_conversion_config

    step = ImgConversionStep(
        config=cfg,
        debugger=runner.debugger,
        logger=runner.logger,
    )

    runner.run_on_directory(step=step)
    runner.logger.info("Image conversion testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test image conversion")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)
