from scripts.module_test_runner import StepTestRunner
from steps.binarization import BinarizationStep
import argparse
import sys
from pathlib import Path

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main(config_path: str):
    runner = StepTestRunner(config_path)

    step = BinarizationStep(
        config=runner.cfg.binarization_config,
        debugger=runner.debugger,
        logger=runner.logger
    )

    runner.run_on_directory(
        step=step,
        output_suffix="_binarized"
    )

    runner.logger.info("Binarization testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test binarization on images")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)
