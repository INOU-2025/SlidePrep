from src.steps import StitchingStep
from src.scripts.test_runner import StepTestRunner
import argparse
import sys
from pathlib import Path

# Ensure project root on Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main(config_path: str) -> None:
    runner = StepTestRunner(config_path)

    step = StitchingStep(
        config=runner.cfg.stitching_config,
        debugger=runner.debugger,
        logger=runner.logger,
    )

    tiles_dir = (
        runner.cfg.test_config.input_path
        if runner.cfg.test_config and runner.cfg.test_config.input_path
        else runner.cfg.general_config.output_path
    )
    step.run(tiles_dir)

    runner.logger.info("Stitching testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Ashlar stitching step")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()
    main(args.config)
