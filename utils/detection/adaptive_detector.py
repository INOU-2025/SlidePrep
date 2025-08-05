import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import logging

from config.config_schema import GridDetectionConfig
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

    def __init__(self, grid_config: GridDetectionConfig):
        """
        Initialize the adaptive line detector from grid configuration.

        Args:
            grid_config: GridDetectionConfig instance with all settings
        """
        # Extract parameters from config
        self.min_contour_area = grid_config.min_contour_area
        self.threshold = grid_config.threshold
        self.angles = grid_config.angles

        # Performance optimizations from config
        self.enable_early_exit = grid_config.enable_early_exit
        self.enable_template_cache = grid_config.enable_template_cache
        self.enable_preprocessing_cache = grid_config.enable_preprocessing_cache
        self.cache_max_size = grid_config.cache_max_size

        # Strategy configurations from config
        self.configs = {
            DetectionStrategy.GENERAL: grid_config.general,
            DetectionStrategy.THICK_BORDER: grid_config.thick_border,
            DetectionStrategy.THIN_BORDER: grid_config.thin_border
        }

        # Initialize caches
        self.template_cache = TemplateCache() if self.enable_template_cache else None
        self.preprocessing_cache = ImagePreprocessingCache(
            max_size=self.cache_max_size
        ) if self.enable_preprocessing_cache else None

        # Storage for detection results
        self.detection_results = {}
        self.strategies_used = {}

    def _get_preprocessed_image(self, image: np.ndarray) -> np.ndarray:
        """Get preprocessed (inverted) image with caching."""
        if self.preprocessing_cache:
            return self.preprocessing_cache.get_inverted_image(image)
        return cv2.bitwise_not(image)

    def _get_templates(self, strategy: DetectionStrategy, orientation: str) -> List[np.ndarray]:
        """Get templates for the given strategy and orientation."""
        config = self.configs[strategy]

        if self.template_cache:
            # Use global threshold and angles instead of config-specific ones
            cache_config = {**config, 'threshold': self.threshold, 'angles': self.angles}
            return self.template_cache.get_templates(strategy, orientation, cache_config)

        return [generate_blurred_template(
            config['template_length'],
            config['thickness'],
            angle,
            orientation
        ) for angle in self.angles]  # Use global angles

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
        mask = create_detection_mask(response_map, self.threshold)  # Use global threshold

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
        """Detect lines using adaptive strategy progression."""
        logger = logging.getLogger(__name__)
        
        self.detection_results = {}
        self.strategies_used = {}

        missing_orientations = ['horizontal', 'vertical']

        # Strategy 1: General detection
        logger.info("Trying general detection...")

        for orientation in missing_orientations[:]:
            logger.info(f"Processing {orientation} orientation...")

            mask, contours = self._detect_single_orientation(
                image, DetectionStrategy.GENERAL, orientation)

            if has_valid_detections(contours, self.min_contour_area):
                self.detection_results[orientation] = (mask, contours)
                self.strategies_used[orientation] = DetectionStrategy.GENERAL
                missing_orientations.remove(orientation)
                logger.info(f"✓ Found {len(contours)} {orientation} lines")
            else:
                logger.info(f"✗ No {orientation} lines found")

        # Early exit optimization
        if self.enable_early_exit and not missing_orientations:
            logger.info("✓ Early exit: Both orientations found in general detection")
            return self._create_result_dict(missing_orientations)

        # Strategy 2: Thick border detection
        if missing_orientations:
            logger.info(
                f"Trying thick border detection for missing orientations: {missing_orientations}")

            for orientation in missing_orientations[:]:
                logger.info(f"Processing {orientation} orientation...")

                mask, contours = self._detect_single_orientation(
                    image, DetectionStrategy.THICK_BORDER, orientation)

                if has_valid_detections(contours, self.min_contour_area):
                    self.detection_results[orientation] = (mask, contours)
                    self.strategies_used[orientation] = DetectionStrategy.THICK_BORDER
                    missing_orientations.remove(orientation)
                    logger.info(f"✓ Found {len(contours)} {orientation} lines")
                else:
                    logger.info(f"✗ No {orientation} lines found")

        # Early exit optimization
        if self.enable_early_exit and not missing_orientations:
            logger.info("✓ Early exit: Both orientations found in thick border detection")
            return self._create_result_dict(missing_orientations)

        # Strategy 3: Thin border detection
        if missing_orientations:
            logger.info(
                f"Trying thin border detection for remaining orientations: {missing_orientations}")

            for orientation in missing_orientations[:]:
                logger.info(f"Processing {orientation} orientation...")

                mask, contours = self._detect_single_orientation(
                    image, DetectionStrategy.THIN_BORDER, orientation)

                if has_valid_detections(contours, self.min_contour_area):
                    self.detection_results[orientation] = (mask, contours)
                    self.strategies_used[orientation] = DetectionStrategy.THIN_BORDER
                    missing_orientations.remove(orientation)
                    logger.info(f"✓ Found {len(contours)} {orientation} lines")
                else:
                    logger.info(f"✗ No {orientation} lines found")

        return self._create_result_dict(missing_orientations)

    def _create_result_dict(self, missing_orientations: List[str]) -> Dict[str, Any]:
        """Create standardized result dictionary."""
        # Handle any still missing orientations
        if missing_orientations:
            for orientation in missing_orientations:
                self.detection_results[orientation] = (
                    np.zeros((100, 100), dtype=np.uint8), [])
                self.strategies_used[orientation] = None

        # Print final summary
        logger = logging.getLogger(__name__)
        logger.info("Detection Summary:")
        for orientation in ['horizontal', 'vertical']:
            strategy = self.strategies_used.get(orientation)
            if strategy:
                mask, contours = self.detection_results[orientation]
                valid_count = len(
                    [c for c in contours if cv2.contourArea(c) >= self.min_contour_area])
                logger.info(
                    f"  {orientation.capitalize()}: {valid_count} lines using {strategy.value}")
            else:
                logger.info(f"  {orientation.capitalize()}: No lines found")

        # Print cache performance
        cache_stats = self.get_cache_info()
        logger.info(f"Cache Performance:")
        logger.info(
            f"  Template cache - Hits: {cache_stats['template_cache_hits']}, Misses: {cache_stats['template_cache_misses']}")
        logger.info(
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
        logger = logging.getLogger(__name__)
        logger.info("Caches cleared")

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
