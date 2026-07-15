"""CLI script for testing grid detection followed by border-classifier refinement."""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

# Ensure project root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.test_runner import StepTestRunner
from src.steps import GridRefinementStep
from src.utils.debug.detection_drawer import DetectionDrawer
from src.utils.debug.detection_analysis_writer import DetectionAnalysisWriter
from src.utils.debug.detection_result_writer import DetectionResultWriter
from src.utils.debug.multi_result_writer import MultiResultWriter


def main(config_path: str) -> None:
    drawer = DetectionDrawer()
    writer = MultiResultWriter([DetectionResultWriter(), DetectionAnalysisWriter()])

    runner = StepTestRunner(config_path, drawer, writer)

    step = GridRefinementStep(config=runner.cfg.grid_refinement_config)

    runner.run_on_directory(
        step=step
    )

    runner.logger.info("Adaptive grid detection testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test grid refinement")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)