"""ResultWriter subclass that serialises raw detection results to JSON."""

from typing import Any
from .result_writer import ResultWriter
from src.utils.detection  import DetectionResultDict
import json


class DetectionResultWriter(ResultWriter):
    """Result writer for grid detection step."""

    def _save_results_to_json(self, results, metadata, path):
        """Save detection results to a JSON file at path."""
        if not results or not path:
            raise ValueError("No results to save or not valid JSON path.")

        if not path.lower().endswith(".json"):
            path += ".json"

        if isinstance(results, list):
            DetectionResultDict.write_batch(path, results, indent=2)
        else:
            DetectionResultDict(results).to_json(path, indent=2)

    def write(self, path: str, results: Any, metadata: Any = None) -> None:
        """Serialize detection results to a JSON file.

        Args:
            path: Destination JSON file path.
            results: Detection results from the grid detection step.
            metadata: Optional metadata.
        """
        try:
            self._save_results_to_json(results, metadata, path)
        except Exception as e:
            raise RuntimeError(
                f"Failed to write grid detection results to JSON: {e}")
