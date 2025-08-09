"""Grid refinement step to post-process detection results."""

from typing import Any, Dict, List, Optional

from core.step import PipelineStep
from config.config_schema import GridRefinementConfig
from utils.detection.models import DetectionStrategy, Orientation
from utils.detection.contour_analysis import analyze_contour


class GridRefinementStep(PipelineStep):
    """Pipeline step for refining grid detection results."""

    def __init__(self, config: GridRefinementConfig, **kwargs: Any) -> None:
        """Initialize grid refinement step with configuration."""
        super().__init__(name="Grid Refinement", config=config, **kwargs)

    def run(self, data: Any) -> tuple[Dict[str, Any], Optional[dict]]:
        """Refine detection results by analyzing non-general contours.

        Args:
            data: Tuple of (results, metadata) from grid detection step.

        Returns:
            Tuple containing refined results and original metadata.
        """
        if not isinstance(data, tuple) or len(data) != 2:
            raise TypeError("GridRefinementStep expects (results, metadata) tuple")

        results, metadata = data
        if not isinstance(results, dict):
            raise TypeError("GridRefinementStep expects results dictionary")

        detections = results.get("detections", {})
        strategies = results.get("strategies", {})
        refined: Dict[Orientation, Any] = {}

        for orientation, contour_dicts in detections.items():
            strategy = strategies.get(orientation)
            orientation_name = orientation.value if hasattr(orientation, "value") else str(orientation)

            if strategy == DetectionStrategy.GENERAL:
                self.debug(
                    f"Keeping {len(contour_dicts)} {orientation_name} contours from general detection"
                )
                refined[orientation] = contour_dicts
            else:
                self.debug(
                    f"Analyzing {len(contour_dicts)} {orientation_name} contours from {getattr(strategy, 'value', strategy)} detection"
                )
                analyses: List[dict] = []
                for item in contour_dicts:
                    contour = item.get("contour")
                    zone = item.get("zone")
                    info = analyze_contour(contour, orientation=orientation, strategy=strategy)
                    info["zone"] = zone.value if zone else None
                    analyses.append(info)
                refined[orientation] = analyses

        refined_results = {"detections": refined, "strategies": strategies}
        return refined_results, metadata