import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

from .status import DetectionStatus


class DetectionStrategy(Enum):
    """Detection strategy types for adaptive line detection."""
    GENERAL = "general"
    THICK_BORDER = "thick_border"
    THIN_BORDER = "thin_border"


@dataclass
class Detection:
    """
    Represents a single grid line detection with geometric and classification data.

    Contains the complete information about a detected grid line including
    its contour representation, bounding geometry, classification status,
    and orientation. This data structure enables both visualization and
    further analysis of detected grid patterns.
    """
    contour: np.ndarray  # Contour points defining the detected shape
    rotated_box: np.ndarray  # Oriented bounding box corners
    status: DetectionStatus  # Classification result (ACCEPT/REJECT/MAYBE)
    orientation: str  # Grid line orientation ('horizontal' or 'vertical')


@dataclass
class GridDetectionResult:
    """
    Comprehensive results from grid detection analysis.

    Encapsulates all detections found during grid analysis along with
    summary statistics for performance evaluation and debugging. Provides
    both detailed per-detection information and aggregate metrics for
    the overall detection process.
    """
    detections: List[Detection]  # All detected grid line candidates
    stats: Dict[str, int]  # Summary counts by detection status
