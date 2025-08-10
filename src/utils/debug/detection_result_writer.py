from typing import Any
from .result_writer import ResultWriter
from src.utils.conversion_utils import make_json_serializable
import json


class DetectionResultWriter(ResultWriter):
    """Result writer for grid detection step."""

    def _save_results_to_json(self, results, metadata, path, data_is_aggregated):
        """
        Save detection results and optional metadata to a JSON file.

        Args:
            results: Detection results to be saved.
            metadata: Optional metadata associated with the results.
            path: Path to output JSON file.
            data_is_aggregated: If True, include metadata; else, omit.
        """
        if not results or not path:
            raise ValueError("No results to save or not valid JSON path.")

        # Ensure .json extension
        if not path.lower().endswith(".json"):
            path += ".json"

        serializable_results = make_json_serializable(results)
        if data_is_aggregated:
            data = {"results": serializable_results}
            if metadata is not None:
                data["metadata"] = make_json_serializable(metadata)
        else:
            data = serializable_results

        with open(path, "w") as f:
            json.dump(data, f)

    def write(self, path: str, results: Any, metadata: Any = None, data_is_aggregated: bool = False) -> None:
        """Serialize detection results to a JSON file.

        Args:
            path: Destination JSON file path.
            results: Detection results from the grid detection step.
            metadata: Optional metadata.
            data_is_aggregated: If True, include metadata; else, omit.
        """
        try:
            self._save_results_to_json(results, metadata, path, data_is_aggregated)
        except Exception as e:
            raise RuntimeError(
                f"Failed to write grid detection results to JSON: {e}")
