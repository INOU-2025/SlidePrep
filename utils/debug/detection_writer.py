from typing import Any
import logging

from .result_writer import ResultWriter
from utils.detection.contour_analysis import analyze_all_contours_for_batch, save_aggregated_analysis_to_csv


class DetectionResultWriter(ResultWriter):
    """Result writer for grid detection step.

    Analyzes detected grid lines and persists analytical metrics to a CSV file.
    """

    def write(self, path: str, results: Any, metadata: Any = None) -> None:
        """Analyze detection results and write them to a CSV file.

        Args:
            path: Destination CSV file path.
            results: Detection results from the grid detection step.
            metadata: Optional metadata, may include image_shape for proximity metrics.
        """
        if not path or results is None:
            return

        try:

            image_shape = None
            if isinstance(metadata, dict):
                image_shape = metadata.get("image_shape")

            analysis_results = analyze_all_contours_for_batch(
                results, image_shape=image_shape
            )
            save_aggregated_analysis_to_csv(analysis_results, path)
        except Exception as e:
            logging.warning(f"Failed to write grid detection results to CSV: {e}")