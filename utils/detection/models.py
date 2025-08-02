"""Data models for grid detection results."""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class Detection:
    """Represents a single grid detection."""
    contour: np.ndarray
    rotated_box: np.ndarray  # 4 corner points of the rotated bounding box
    status: int  # DetectionStatus constant
    orientation: str  # "horizontal", "vertical"


@dataclass
class GridDetectionResult:
    """Results from grid detection analysis."""
    detections: List[Detection]
    summary: Dict[str, int]  # {"accept": count, "reject": count, "maybe": count}
