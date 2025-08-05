import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any

from .models import DetectionStrategy
from .template_utils import generate_blurred_template, perform_template_matching
from .image_preprocessing import create_detection_mask, ImagePreprocessingCache
from .contour_analysis import filter_contours_by_border_zone, has_valid_detections


class TemplateCache:
    """Cache for generated templates."""

    def __init__(self):
        self.cache: Dict[DetectionStrategy, Dict[str, List[np.ndarray]]] = {}
        self.hits = 0
        self.misses = 0

    def get_templates(self, strategy: DetectionStrategy, orientation: str,
                      config: Dict[str, Any]) -> List[np.ndarray]:
        """Get templates with caching."""
        if strategy in self.cache and orientation in self.cache[strategy]:
            self.hits += 1
            return self.cache[strategy][orientation]

        self.misses += 1

        templates = [generate_blurred_template(
            config['template_length'],
            config['thickness'],
            angle,
            orientation
        ) for angle in config['angles']]

        if strategy not in self.cache:
            self.cache[strategy] = {}
        self.cache[strategy][orientation] = templates

        return templates

    def clear(self) -> None:
        """Clear template cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'size': sum(len(orientations) for orientations in self.cache.values())
        }


class AdaptiveLineDetector:
    """
    Sophisticated adaptive line detector that tries multiple strategies.

    Optimizations included:
    - Early exit strategy: Stop when both orientations are found
    - Template caching: Cache templates for repeated use
    - Image preprocessing cache: Cache inverted image for multiple template matches

    Detection Strategy:
    1. General detection (no area restrictions)
    2. If missing orientations: Thick border detection
    3. If still missing orientations: Thin border detection

    Optimized to only process missing orientations in each round.
    """

    def __init__(self, min_contour_area: int = 100, verbose: bool = True,
                 enable_early_exit: bool = True, enable_template_cache: bool = True,
                 enable_preprocessing_cache: bool = True, cache_max_size: int = 50):
        """
        Initialize adaptive detector with optimization options.

        Args:
            min_contour_area: Minimum contour area for valid detection
            verbose: Whether to print detection strategy information
            enable_early_exit: Whether to stop when both orientations found
            enable_template_cache: Whether to cache generated templates
            enable_preprocessing_cache: Whether to cache image preprocessing
            cache_max_size: Maximum size for preprocessing cache
        """
        self.min_contour_area = min_contour_area
        self.verbose = verbose
        self.enable_early_exit = enable_early_exit
        self.enable_template_cache = enable_template_cache
        self.enable_preprocessing_cache = enable_preprocessing_cache
        self.cache_max_size = cache_max_size

        # Configuration for different strategies
        self.configs = {
            DetectionStrategy.GENERAL: {
                'template_length': 300,
                'thickness': 20,
                'threshold': 0.1,
                'angles': [2, -2],
                'border_thickness': 0
            },
            DetectionStrategy.THICK_BORDER: {
                'template_length': 100,
                'thickness': 7,
                'threshold': 0.1,
                'angles': [2, -2],
                'border_thickness': 35
            },
            DetectionStrategy.THIN_BORDER: {
                'template_length': 30,
                'thickness': 7,
                'threshold': 0.1,
                'angles': [2, -2],
                'border_thickness': 20
            }
        }

        # Initialize caches
        self.template_cache = TemplateCache() if enable_template_cache else None
        self.preprocessing_cache = ImagePreprocessingCache(
            max_size=cache_max_size
        ) if enable_preprocessing_cache else None

        # Storage for detection results
        self.detection_results = {}
        self.strategies_used = {}

    def _get_preprocessed_image(self, image: np.ndarray) -> np.ndarray:
        """Get preprocessed (inverted) image with caching."""
        if self.preprocessing_cache:
            return self.preprocessing_cache.get_inverted_image(image)
        return cv2.bitwise_not(image)

    def _get_templates(self, strategy: DetectionStrategy, orientation: str) -> List[np.ndarray]:
        """Get templates with caching."""
        config = self.configs[strategy]

        if self.template_cache:
            return self.template_cache.get_templates(strategy, orientation, config)

        return [generate_blurred_template(
            config['template_length'],
            config['thickness'],
            angle,
            orientation
        ) for angle in config['angles']]

    def _detect_single_orientation(self, image: np.ndarray, strategy: DetectionStrategy,
                                   orientation: str) -> Tuple[np.ndarray, List[np.ndarray]]:
        """
        Detect lines for a single orientation with a specific strategy.
        Uses cached preprocessing and templates for better performance.
        """
        config = self.configs[strategy]

        # Use cached preprocessing
        inverted = self._get_preprocessed_image(image)

        # Use cached templates
        templates = self._get_templates(strategy, orientation)

        # Perform template matching
        response_map = perform_template_matching(inverted, templates)
        mask = create_detection_mask(response_map, config['threshold'])

        # Find contours
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours for border strategies
        if strategy != DetectionStrategy.GENERAL:
            contours = filter_contours_by_border_zone(
                contours, image.shape, config['border_thickness'],
                orientation, self.min_contour_area
            )

        return mask, contours

    def detect_lines(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Adaptively detect lines using multiple strategies as needed.

        Returns:
            Dictionary containing detection results and metadata
        """
        self.detection_results = {}
        self.strategies_used = {}

        missing_orientations = ['horizontal', 'vertical']

        # Strategy 1: General detection
        if self.verbose:
            print("Trying general detection...")

        for orientation in missing_orientations[:]:
            if self.verbose:
                print(f"  Processing {orientation} orientation...")

            mask, contours = self._detect_single_orientation(
                image, DetectionStrategy.GENERAL, orientation)

            if has_valid_detections(contours, self.min_contour_area):
                self.detection_results[orientation] = (mask, contours)
                self.strategies_used[orientation] = DetectionStrategy.GENERAL
                missing_orientations.remove(orientation)
                if self.verbose:
                    valid_count = len(
                        [c for c in contours if cv2.contourArea(c) >= self.min_contour_area])
                    print(f"    ✓ Found {valid_count} {orientation} lines")
            else:
                if self.verbose:
                    print(f"    ✗ No {orientation} lines found")

        # Early exit optimization
        if self.enable_early_exit and not missing_orientations:
            if self.verbose:
                print("✓ Early exit: Both orientations found in general detection")
            return self._create_result_dict(missing_orientations)

        # Strategy 2: Thick border detection
        if missing_orientations:
            if self.verbose:
                print(
                    f"Trying thick border detection for missing orientations: {missing_orientations}")

            for orientation in missing_orientations[:]:
                if self.verbose:
                    print(f"  Processing {orientation} orientation...")

                mask, contours = self._detect_single_orientation(
                    image, DetectionStrategy.THICK_BORDER, orientation)

                if has_valid_detections(contours, self.min_contour_area):
                    self.detection_results[orientation] = (mask, contours)
                    self.strategies_used[orientation] = DetectionStrategy.THICK_BORDER
                    missing_orientations.remove(orientation)
                    if self.verbose:
                        valid_count = len(
                            [c for c in contours if cv2.contourArea(c) >= self.min_contour_area])
                        print(f"    ✓ Found {valid_count} {orientation} lines")
                else:
                    if self.verbose:
                        print(f"    ✗ No {orientation} lines found")

        # Early exit optimization
        if self.enable_early_exit and not missing_orientations:
            if self.verbose:
                print("✓ Early exit: Both orientations found in thick border detection")
            return self._create_result_dict(missing_orientations)

        # Strategy 3: Thin border detection
        if missing_orientations:
            if self.verbose:
                print(
                    f"Trying thin border detection for remaining orientations: {missing_orientations}")

            for orientation in missing_orientations[:]:
                if self.verbose:
                    print(f"  Processing {orientation} orientation...")

                mask, contours = self._detect_single_orientation(
                    image, DetectionStrategy.THIN_BORDER, orientation)

                if has_valid_detections(contours, self.min_contour_area):
                    self.detection_results[orientation] = (mask, contours)
                    self.strategies_used[orientation] = DetectionStrategy.THIN_BORDER
                    missing_orientations.remove(orientation)
                    if self.verbose:
                        valid_count = len(
                            [c for c in contours if cv2.contourArea(c) >= self.min_contour_area])
                        print(f"    ✓ Found {valid_count} {orientation} lines")
                else:
                    if self.verbose:
                        print(f"    ✗ No {orientation} lines found")

        return self._create_result_dict(missing_orientations)

    def _create_result_dict(self, missing_orientations: List[str]) -> Dict[str, Any]:
        """Create standardized result dictionary."""
        # Handle any still missing orientations
        if missing_orientations:
            if self.verbose:
                print(
                    f"Final result: Could not find lines for {missing_orientations}")
            for orientation in missing_orientations:
                self.detection_results[orientation] = (
                    np.zeros((100, 100), dtype=np.uint8), [])
                self.strategies_used[orientation] = None

        # Print final summary
        if self.verbose:
            print("\nDetection Summary:")
            for orientation in ['horizontal', 'vertical']:
                strategy = self.strategies_used.get(orientation)
                if strategy:
                    mask, contours = self.detection_results[orientation]
                    valid_count = len(
                        [c for c in contours if cv2.contourArea(c) >= self.min_contour_area])
                    print(
                        f"  {orientation.capitalize()}: {valid_count} lines using {strategy.value}")
                else:
                    print(f"  {orientation.capitalize()}: No lines found")

            # Print cache performance
            cache_stats = self.get_cache_info()
            print(f"\nCache Performance:")
            print(
                f"  Template cache - Hits: {cache_stats['template_cache_hits']}, Misses: {cache_stats['template_cache_misses']}")
            print(
                f"  Preprocessing cache - Hits: {cache_stats['preprocessing_cache_hits']}, Misses: {cache_stats['preprocessing_cache_misses']}")

        return {
            'detections': self.detection_results,
            'strategies': self.strategies_used,
            'missing': missing_orientations,
            'cache_stats': self.get_cache_info()
        }

    def clear_caches(self) -> None:
        """Clear all caches to free memory."""
        if self.template_cache:
            self.template_cache.clear()
        if self.preprocessing_cache:
            self.preprocessing_cache.clear()
        if self.verbose:
            print("Caches cleared")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cache usage."""
        template_stats = self.template_cache.get_stats() if self.template_cache else {
            'hits': 0, 'misses': 0, 'size': 0}
        preprocessing_stats = self.preprocessing_cache.get_stats(
        ) if self.preprocessing_cache else {'hits': 0, 'misses': 0, 'size': 0}

        return {
            'template_cache_size': template_stats['size'],
            'preprocessing_cache_size': preprocessing_stats['size'],
            'template_cache_hits': template_stats['hits'],
            'template_cache_misses': template_stats['misses'],
            'preprocessing_cache_hits': preprocessing_stats['hits'],
            'preprocessing_cache_misses': preprocessing_stats['misses']
        }
