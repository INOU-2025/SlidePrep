import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

# Ensure project root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.step import PipelineStep
from src.scripts.module_test_runner import StepTestRunner
from src.steps import GridDetectionStep, GridRefinementStep
from src.utils.debug.detection_drawer import DetectionDrawer
from utils.debug.detection_analysis_writer import DetectionAnalysisWriter


class DetectionRefinementStep(PipelineStep):
    """Composite step running detection followed by refinement."""

    def __init__(
        self,
        detection_step: GridDetectionStep,
        refinement_step: GridRefinementStep,
    ) -> None:
        super().__init__(name="grid_detection_refinement")
        self._detection_step = detection_step
        self._refinement_step = refinement_step

    def run(self, image: np.ndarray) -> Tuple[Dict[str, Any], Optional[dict]]:
        """Run grid detection and refine the results."""
        detection_output = self._detection_step.run(image)
        return self._refinement_step.run(detection_output)


def main(config_path: str) -> None:
    """Test grid refinement on all images in the input directory."""
    drawer = DetectionDrawer()
    writer = DetectionAnalysisWriter()

    runner = StepTestRunner(config_path, drawer, writer)

    detection_step = GridDetectionStep(
        config=runner.cfg.grid_detection_config,
        debugger=runner.debugger,
        logger=runner.logger,
    )

    refinement_step = GridRefinementStep(
        config=runner.cfg.grid_refinement_config,
        debugger=runner.debugger,
        logger=runner.logger,
    )

    composite_step = DetectionRefinementStep(detection_step, refinement_step)

    runner.run_on_directory(step=composite_step)
    runner.logger.info("Grid refinement testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test grid refinement on images")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)