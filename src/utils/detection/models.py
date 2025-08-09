from enum import Enum


class DetectionStrategy(Enum):
    """Detection strategy types for adaptive line detection."""
    GENERAL = "general"
    THICK_BORDER = "thick_border"
    THIN_BORDER = "thin_border"

class DetectionRegion(Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"

class Orientation(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
