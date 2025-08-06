from enum import Enum


class DetectionStrategy(Enum):
    """Detection strategy types for adaptive line detection."""
    GENERAL = "general"
    THICK_BORDER = "thick_border"
    THIN_BORDER = "thin_border"
