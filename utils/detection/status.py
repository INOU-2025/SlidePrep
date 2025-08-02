"""Detection status constants and utilities."""

from enum import Enum
from typing import Tuple


class DetectionStatus(Enum):
    """Enumerates possible detection outcomes."""

    ACCEPT = 0
    REJECT = 1
    MAYBE = 2

    def __str__(self) -> str:
        """Return lower-case name for easier logging/debugging."""
        return self.name.lower()

    @classmethod
    def to_string(cls, status: "DetectionStatus") -> str:
        """Convert status enum to string representation."""
        return str(status)

    @classmethod
    def get_color(cls, status: "DetectionStatus") -> Tuple[int, int, int]:
        """Get BGR color for visualization based on status."""
        mapping = {
            cls.ACCEPT: (0, 255, 0),  # Green
            cls.REJECT: (0, 0, 255),  # Red
            cls.MAYBE: (0, 255, 255),  # Yellow
        }
        return mapping.get(status, (128, 128, 128))  # Gray for unknown
