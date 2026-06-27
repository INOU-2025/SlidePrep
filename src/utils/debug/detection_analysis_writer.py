"""ResultWriter subclass that saves per-contour analysis metrics to CSV."""

from typing import Any
import csv

from .result_writer import ResultWriter
from src.utils.conversion_utils import make_csv_serializable


class DetectionAnalysisWriter(ResultWriter):
    """Analysis writer for grid detection step.

    Analyzes detected grid lines and persists analytical metrics to a CSV file that are used later on to train a detection classification model.
    """

    def _save_aggregated_analysis_to_csv(self, analysis_results, csv_path):
        """
        Save aggregated contour analysis results to a CSV file.
        Args:
            analysis_results: List of analysis result dicts (from analyze_all_contours_from_results)
            csv_path: Path to output CSV file
        """
        if not analysis_results or not csv_path:
            raise ValueError(
                "No analysis results to save or not valid CSV path.")

        if not csv_path.lower().endswith(".csv"):
            csv_path += ".csv"

        fieldnames = list(analysis_results[0].keys())
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in analysis_results:
                flat_row = {k: make_csv_serializable(
                    v) for k, v in row.items()}
                writer.writerow(flat_row)

    def write(self, path: str, results: Any, metadata: Any = None) -> None:
        """Analyze detection results and write them to a CSV file.

        Args:
            path: Destination CSV file path.
            results: Detection results from the grid detection step.
            metadata: Optional metadata, may include image_shape for proximity metrics.
        """
        try:
            from src.utils.detection.contour_analysis import analyze_all_contours_for_batch

            image_shape = None
            if isinstance(metadata, dict):
                image_shape = metadata.get("image_shape")

            analysis_results = analyze_all_contours_for_batch(
                results, image_shape=image_shape
            )
            self._save_aggregated_analysis_to_csv(analysis_results, path)

        except Exception as e:
            raise RuntimeError(
                f"Failed to write grid detection analysis results to CSV: {e}")
