import numpy as np
from typing import Dict

'''
Utility functions for data conversion and manipulation.
'''

SUPPORTED_IMAGE_FORMATS: Dict[str, str] = {
    "jpeg": ".jpeg",
    "png": ".png",
    "tiff": ".tif",
}

def make_csv_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_csv_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_csv_serializable(v) for v in obj]
    elif hasattr(obj, "value"):
        return obj.value
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


def validate_image_format(fmt: str) -> str:
    """Validate and normalize an image format name."""
    fmt_lower = fmt.lower()
    if fmt_lower not in SUPPORTED_IMAGE_FORMATS:
        valid = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS.keys()))
        raise ValueError(f"Unsupported image format: {fmt}. Valid formats: {valid}")
    return fmt_lower


def get_extension_for_format(fmt: str) -> str:
    """Return the file extension for the specified image format."""
    return SUPPORTED_IMAGE_FORMATS[validate_image_format(fmt)]
