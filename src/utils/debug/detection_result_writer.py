from typing import Any
from .result_writer import ResultWriter
from src.utils.conversion_utils import make_json_serializable
import json


class DetectionResultWriter(ResultWriter):
    """Result writer for grid detection step.
    """

    def _save_aggregated_results_to_json(self, results, metadata, path):
        """
        Save aggregated detection results and metadata to a JSON file.

        Args:
            results: Detection results to be saved.
            metadata: Optional metadata associated with the results.
            path: Path to output JSON file.
        """
        if not results or not path:
            raise ValueError("No results to save or not valid JSON path.")

        # Ensure .json extension
        if not path.lower().endswith(".json"):
            path += ".json"

        serializable_results = make_json_serializable(results)
        serializable_metadata = make_json_serializable(metadata)

        with open(path, "w") as f:
            json.dump({"results": serializable_results,
                       "metadata": serializable_metadata}, f)

    def write(self, path: str, results: Any, metadata: Any = None) -> None:
        """Serialize detection results to a JSON file.

        Args:
            path: Destination JSON file path.
            results: Detection results from the grid detection step.
            metadata: Optional metadata.
        """
        try:
            self._save_aggregated_results_to_json(results, metadata, path)
        except Exception as e:
            raise RuntimeError(
                f"Failed to write grid detection results to JSON: {e}")
