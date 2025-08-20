import os
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image


def get_supported_image_formats() -> Tuple[str, ...]:
    """
    Get tuple of supported image file extensions (lowercase).

    Returns:
        Tuple of supported file extensions including the dot (e.g., '.png', '.jpg')
    """
    return (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")


def get_supported_image_patterns() -> List[str]:
    """
    Get list of glob patterns for supported image formats.

    Returns:
        List of glob patterns (e.g., ['*.png', '*.jpg', ...])
    """
    formats = get_supported_image_formats()
    return [f"*{ext}" for ext in formats]


def is_supported_image_file(filename: str) -> bool:
    """
    Check if a filename has a supported image extension.

    Args:
        filename: The filename to check

    Returns:
        True if the file extension is supported, False otherwise
    """
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


def crop_image_padding(
    image_path: str,
    bbox: Tuple[int, int, int, int],
    output_path: str,
    padding: int = 0,
) -> None:
    """Crop an image using OpenCV and save the result.

    Parameters
    ----------
    image_path:
        Path to the source image file.
    bbox:
        Bounding box defined as ``(x_min, y_min, x_max, y_max)``.
    output_path:
        Destination file path for the cropped image.
    padding:
        Optional number of pixels to pad around the bounding box.

    Raises
    ------
    FileNotFoundError
        If the image cannot be read from ``image_path``.
    ValueError
        If the resulting crop is empty.
    """

    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Unable to read image: {image_path}")

    x_min, y_min, x_max, y_max = bbox
    height, width = image.shape[:2]

    x_min = max(x_min - padding, 0)
    y_min = max(y_min - padding, 0)
    x_max = min(x_max + padding, width)
    y_max = min(y_max + padding, height)

    cropped = image[y_min:y_max, x_min:x_max]
    if cropped.size == 0:
        raise ValueError("Crop area is empty")

    if cropped.dtype != np.uint8:
        cropped = cropped.astype(np.uint8)

    cv2.imwrite(output_path, cropped)
