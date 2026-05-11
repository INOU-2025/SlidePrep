from typing import Any, Dict, Optional

import numpy as np


class StepResult:
    """
    Standardized result object for pipeline steps.
    Supports unpacking as (data, metadata) for backward compatibility.
    """
    def __init__(self, data: Any, metadata: Optional[Dict[str, Any]] = None):
        self.data = data
        self.metadata = metadata

    @classmethod
    def from_data(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "StepResult":
        return cls(data, metadata)

    @classmethod
    def from_array(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "StepResult":
        return cls(data, metadata)

    def to_array(self) -> Any:
        return self.data

    @property
    def image(self) -> Any:
        if isinstance(self.data, np.ndarray):
            return self.data
        return None

