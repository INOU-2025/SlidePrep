"""Detection status constants and utilities."""

from typing import Tuple


class DetectionStatus:
    """Constants for detection status values."""
    ACCEPT = 0
    REJECT = 1
    MAYBE = 2
    
    @classmethod
    def to_string(cls, status: int) -> str:
        """Convert status integer to string representation."""
        mapping = {
            cls.ACCEPT: "accept",
            cls.REJECT: "reject", 
            cls.MAYBE: "maybe"
        }
        return mapping.get(status, "unknown")
    
    @classmethod
    def get_color(cls, status: int) -> Tuple[int, int, int]:
        """Get BGR color for visualization based on status."""
        mapping = {
            cls.ACCEPT: (0, 255, 0),    # Green
            cls.REJECT: (0, 0, 255),    # Red
            cls.MAYBE: (0, 255, 255)    # Yellow
        }
        return mapping.get(status, (128, 128, 128))  # Gray for unknown
