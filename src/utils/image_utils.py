"""Filesystem and format helpers for loading and filtering pipeline input images."""

import os
from typing import List, Tuple

import numpy as np
from PIL import Image


def get_supported_image_formats() -> Tuple[str, ...]:
    """Dot-prefixed, lowercase extension strings for all supported input formats."""
    return (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")


def get_supported_image_patterns() -> List[str]:
    """Glob patterns (e.g. '*.png') for all supported input image formats."""
    formats = get_supported_image_formats()
    return [f"*{ext}" for ext in formats]


def is_supported_image_file(filename: str) -> bool:
    """Return True if filename has a supported image extension."""
    return filename.lower().endswith(get_supported_image_formats())


def filter_images_by_suffix(image_paths: list[str], suffix: str) -> list[str]:
    """
    Filter a list of image paths by a suffix applied to the filename without extension.

    Args:
        image_paths: List of image file paths
        suffix: Suffix to filter by (e.g., '_ch00', '_processed')

    Returns:
        Filtered list of image paths where filename ends with the specified suffix

    Example:
        filter_images_by_suffix(['sample_001_ch00.jpg', 'sample_001_ch01.jpg'], '_ch00')
        Returns: ['sample_001_ch00.jpg']
    """
    if not suffix:
        return image_paths

    filtered_paths = []
    for path in image_paths:
        filename = os.path.basename(path)
        name_without_ext = os.path.splitext(filename)[0]
        if name_without_ext.endswith(suffix):
            filtered_paths.append(path)

    return filtered_paths


def convert_image_mode(image: np.ndarray, mode: str) -> np.ndarray:
    """Convert an image array to the specified mode.

    Args:
        image: Input image as a NumPy array.
        mode: Target mode - ``"RGB"`` or ``"grayscale"`` (``"greyscale"``).

    Returns:
        Image converted to the requested mode.

    Raises:
        ValueError: If an unsupported mode is provided.
    """
    pil_img = Image.fromarray(image)
    mode_upper = mode.upper()

    if mode_upper == "RGB":
        return np.asarray(pil_img.convert("RGB"))
    if mode_upper in {"L", "GRAYSCALE", "GREYSCALE"}:
        return np.asarray(pil_img.convert("L"))
    raise ValueError(f"Unsupported image mode: {mode}")
