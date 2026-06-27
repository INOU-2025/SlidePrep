from typing import Any, Dict, Optional

import numpy as np


class StepResult:
    """Standardized result object returned by every pipeline step."""

    def __init__(self, data: Any, metadata: Optional[Dict[str, Any]] = None):
        self.data = data
        self.metadata = metadata

    @classmethod
    def from_data(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "StepResult":
        """Alias for the constructor; prefer direct construction."""
        return cls(data, metadata)

    @classmethod
    def from_array(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "StepResult":
        """Alias for the constructor; prefer direct construction."""
        return cls(data, metadata)

    def to_array(self) -> Any:
        """Return data as-is for callers expecting an array-like."""
        return self.data

    @property
    def image(self) -> Any:
        """data cast as ndarray, or None if data is not an ndarray."""
        if isinstance(self.data, np.ndarray):
            return self.data
        return None

