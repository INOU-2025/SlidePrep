import cv2
import numpy as np
import hashlib
from typing import Dict


def create_detection_mask(response_map: np.ndarray, threshold: float) -> np.ndarray:
    """
    Create binary mask from template matching response.

    Args:
        response_map: Template matching response
        threshold: Detection threshold

    Returns:
        Binary mask (255 for detections, 0 for background)
    """
    return (response_map < threshold).astype(np.uint8) * 255


class ImagePreprocessingCache:
    """
    Cache for preprocessed images to improve performance.
    """

    def __init__(self, max_size: int = 50):
        self.cache: Dict[str, np.ndarray] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def _get_image_hash(self, image: np.ndarray) -> str:
        """Generate hash for image caching."""
        return hashlib.md5(image.tobytes()).hexdigest()

    def get_inverted_image(self, image: np.ndarray) -> np.ndarray:
        """Get preprocessed (inverted) image with caching."""
        img_hash = self._get_image_hash(image)

        if img_hash in self.cache:
            self.hits += 1
            return self.cache[img_hash]

        self.misses += 1
        inverted = cv2.bitwise_not(image)

        # Manage cache size
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[img_hash] = inverted
        return inverted

    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'size': len(self.cache)
        }
