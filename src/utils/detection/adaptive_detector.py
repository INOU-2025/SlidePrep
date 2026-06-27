import cv2
import numpy as np
from typing import Any, Dict, List, Optional
from logging import Logger, getLogger

from src.config import GridDetectionConfig
from .models import DetectionStrategy, DetectionRegion, Orientation
from .template_utils import generate_blurred_template, perform_template_matching
from .image_preprocessing import create_detection_mask, ImagePreprocessingCache
from .contour_analysis import filter_contours_by_border_zone, analyze_contour


class TemplateCache:
    """Cache for generated templates."""

    def __init__(self):
        self.cache: Dict[DetectionStrategy, Dict[str, List[np.ndarray]]] = {}
        self.hits = 0
        self.misses = 0

    def get_templates(self, strategy: DetectionStrategy, orientation: str,
                      config: Dict[str, Any]) -> List[np.ndarray]:
        """Return cached templates for strategy+orientation, generating them on first miss."""
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
    Adaptive line detector that tries multiple strategies.

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

    def __init__(self, grid_config: GridDetectionConfig, logger: Optional[Logger] = None):
        """
        Initialize the adaptive line detector from grid configuration.

        Args:
            grid_config: GridDetectionConfig instance with all settings
            logger: Optional logger instance for debug and info messages. If ``None``,
                a module-level logger is used.
        """
        self.logger = logger or getLogger(__name__)

        self.threshold = grid_config.threshold
        self.angles = grid_config.angles

        self.enable_early_exit = grid_config.enable_early_exit
        self.enable_template_cache = grid_config.enable_template_cache
        self.enable_preprocessing_cache = grid_config.enable_preprocessing_cache
        self.cache_max_size = grid_config.cache_max_size

        self.configs = {
            DetectionStrategy.GENERAL: grid_config.general or {},
            DetectionStrategy.THICK_BORDER: grid_config.thick_border or {},
            DetectionStrategy.THIN_BORDER: grid_config.thin_border or {}
        }

        self.template_cache = TemplateCache() if self.enable_template_cache else None
        self.preprocessing_cache = ImagePreprocessingCache(
            max_size=self.cache_max_size
        ) if self.enable_preprocessing_cache else None

        self.detection_results: Dict[Orientation, List[dict]] = {}
        self.strategies_used: Dict[Orientation, Optional[DetectionStrategy]] = {}

    def _get_preprocessed_image(self, image: np.ndarray) -> np.ndarray:
        """Get preprocessed (inverted) image with caching."""
        if self.preprocessing_cache:
            return self.preprocessing_cache.get_inverted_image(image)
        return cv2.bitwise_not(image)

    def _get_templates(self, strategy: DetectionStrategy, orientation: Orientation) -> List[np.ndarray]:
        """Get templates for the given strategy and orientation."""
        config = self.configs[strategy]

        if self.template_cache:
            # Use global threshold and angles instead of config-specific ones
            cache_config = {**config, 'threshold': self.threshold, 'angles': self.angles}
            return self.template_cache.get_templates(strategy, orientation.value, cache_config)

        # Use global angles, fallback to empty list if None
        angles = self.angles if self.angles is not None else []
        return [generate_blurred_template(
            config['template_length'],
            config['thickness'],
            angle,
            orientation.value
        ) for angle in angles]  # Use global angles

    def _apply_template_offset_correction(self, contour_dicts: List[dict], 
                                        config: Dict[str, Any], orientation: Orientation) -> List[dict]:
        """
        Apply template offset correction to contours based on orientation.
        
        Args:
            contour_dicts: List of contours {'contour': ..., 'zone': ...} to correct
            config: Strategy configuration with template_length and thickness
            orientation: Orientation enum
            
        Returns:
            List of corrected contours {'contour': corrected_contour, 'zone': zone}
        """
        if not contour_dicts:
            return contour_dicts

        # Calculate orientation-specific offsets
        if orientation == Orientation.HORIZONTAL:
            offset_x = config['template_length'] // 2
            offset_y = config['thickness'] // 2
        else:
            offset_x = config['thickness'] // 2
            offset_y = config['template_length'] // 2
        corrected = []
        for item in contour_dicts:
            contour = item['contour']
            zone = item['zone']
            corrected_contour = contour + np.array([offset_x, offset_y], dtype=np.int32)
            corrected.append({'contour': corrected_contour, 'zone': zone})
        return corrected

    def _detect_single_orientation(self, image: np.ndarray, strategy: DetectionStrategy,
                                   orientation: Orientation) -> List[dict]:
        """
        Detect lines for a single orientation with a specific strategy.
        Uses cached preprocessing and templates for better performance.
        """
        config = self.configs[strategy]

        inverted = self._get_preprocessed_image(image)

        templates = self._get_templates(strategy, orientation)

        response_map = perform_template_matching(inverted, templates)
        mask = create_detection_mask(response_map, self.threshold)  # Use global threshold

        # Find contours using mask (mask not needed beyond this point)
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter by minimum area first (early filtering for performance)
        min_area = config["min_contour_area"]
        area_filtered_contours = [
            cnt for cnt in contours if cv2.contourArea(cnt) >= min_area
        ]

        # Filter contours for border strategies (only process area-valid contours)
        if strategy != DetectionStrategy.GENERAL:
            # Only pass height and width, not full shape tuple
            height, width = image.shape[:2]
            border_filtered_contours = filter_contours_by_border_zone(
                area_filtered_contours, (height, width), config['border_thickness'], orientation
            )
        else:
            border_filtered_contours = [{'contour': cnt, 'zone': DetectionRegion.CENTER} for cnt in area_filtered_contours]

        # Apply template offset correction (only to final valid contours)
        final_contours = self._apply_template_offset_correction(
            border_filtered_contours, config, orientation)

        return final_contours

    def detect_lines(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect lines using adaptive strategy progression."""
        logger = self.logger

        self.detection_results = {}
        self.strategies_used = {}

        missing_orientations = [Orientation.HORIZONTAL, Orientation.VERTICAL]

        # Strategy 1: General detection
        if logger:
            logger.info("Trying general detection...")

        for orientation in missing_orientations[:]:
            if logger:
                logger.info(f"Processing {orientation.value} orientation...")

            contour_dicts = self._detect_single_orientation(
                image, DetectionStrategy.GENERAL, orientation)

            if contour_dicts:
                self.detection_results[orientation] = contour_dicts
                self.strategies_used[orientation] = DetectionStrategy.GENERAL
                missing_orientations.remove(orientation)
                if logger:
                    logger.info(f"✓ Found {len(contour_dicts)} {orientation.value} lines")
            else:
                if logger:
                    logger.info(f"✗ No {orientation.value} lines found")

        # Early exit optimization
        if self.enable_early_exit and not missing_orientations:
            if logger:
                logger.info("✓ Early exit: Both orientations found in general detection")
            return self._create_result_dict(missing_orientations)

        # Strategy 2: Thick border detection
        if missing_orientations:
            if logger:
                logger.info(
                    f"Trying thick border detection for missing orientations: {[o.value for o in missing_orientations]}")

            for orientation in missing_orientations[:]:
                if logger:
                    logger.info(f"Processing {orientation.value} orientation...")

                contour_dicts = self._detect_single_orientation(
                    image, DetectionStrategy.THICK_BORDER, orientation)

                if contour_dicts:
                    self.detection_results[orientation] = contour_dicts
                    self.strategies_used[orientation] = DetectionStrategy.THICK_BORDER
                    missing_orientations.remove(orientation)
                    if logger:
                        logger.info(f"✓ Found {len(contour_dicts)} {orientation.value} lines")
                else:
                    if logger:
                        logger.info(f"✗ No {orientation.value} lines found")

        # Early exit optimization
        if self.enable_early_exit and not missing_orientations:
            if logger:
                logger.info("✓ Early exit: Both orientations found in thick border detection")
            return self._create_result_dict(missing_orientations)

        # Strategy 3: Thin border detection
        if missing_orientations:
            if logger:
                logger.info(
                    f"Trying thin border detection for remaining orientations: {[o.value for o in missing_orientations]}")

            for orientation in missing_orientations[:]:
                if logger:
                    logger.info(f"Processing {orientation.value} orientation...")

                contour_dicts = self._detect_single_orientation(
                    image, DetectionStrategy.THIN_BORDER, orientation)

                if contour_dicts:
                    self.detection_results[orientation] = contour_dicts
                    self.strategies_used[orientation] = DetectionStrategy.THIN_BORDER
                    missing_orientations.remove(orientation)
                    if logger:
                        logger.info(f"✓ Found {len(contour_dicts)} {orientation.value} lines")
                else:
                    if logger:
                        logger.info(f"✗ No {orientation.value} lines found")

        return self._create_result_dict(missing_orientations)
    
    def analyze_results(self, results: dict) -> dict:
        """Return per-contour geometry analysis keyed by orientation string.

        Accepts the dict produced by detect_lines and enriches each detected
        contour with bounding-box metrics from analyze_contour.
        """
        logger = self.logger
        analysis = {}
        for orientation in [Orientation.HORIZONTAL, Orientation.VERTICAL]:
            orientation_analysis = []
            if orientation in results.get('detections', {}):
                contour_dicts = results['detections'][orientation]
                strategy = results['strategies'].get(orientation)
                for idx, item in enumerate(contour_dicts):
                    contour = item['contour']
                    zone = item['zone']
                    if logger:
                        logger.debug(
                            f"Analyzing contour {idx+1}/{len(contour_dicts)} for orientation: {orientation.value}, strategy: {getattr(strategy, 'value', strategy)}, zone: {zone.value if zone else None}"
                        )
                    contour_info = analyze_contour(contour, orientation=orientation, strategy=strategy)
                    contour_info['zone'] = zone.value if zone else None
                    orientation_analysis.append(contour_info)
            analysis[orientation.value] = orientation_analysis
        return analysis

    def _create_result_dict(self, missing_orientations: List[Orientation]) -> Dict[str, Any]:
        """Create standardized result dictionary."""
        if missing_orientations:
            for orientation in missing_orientations:
                self.detection_results[orientation] = []
                self.strategies_used[orientation] = None

        logger = self.logger
        logger.info("Detection Summary:")
        for orientation in [Orientation.HORIZONTAL, Orientation.VERTICAL]:
            strategy = self.strategies_used.get(orientation)
            if strategy:
                contours = self.detection_results[orientation]
                valid_count = len(contours)
                if logger:
                    logger.info(
                        f"  {orientation.value.capitalize()}: {valid_count} lines using {strategy.value}")
            else:
                if logger:
                    logger.info(f"  {orientation.value.capitalize()}: No lines found")

        cache_stats = self.get_cache_info()
        if logger:
            logger.info(f"Cache Performance:")
            logger.info(
                f"  Template cache - Hits: {cache_stats['template_cache_hits']}, Misses: {cache_stats['template_cache_misses']}")
            logger.info(
                f"  Preprocessing cache - Hits: {cache_stats['preprocessing_cache_hits']}, Misses: {cache_stats['preprocessing_cache_misses']}")

        return {
            'detections': self.detection_results,
            'strategies': self.strategies_used
        }
    
    def get_detection_metadata(self) -> Dict[str, Any]:
        """Get detection metadata separately from core results."""
        # Calculate border thicknesses for used strategies
        border_configs = {}
        for orientation, strategy in self.strategies_used.items():
            if strategy and strategy != DetectionStrategy.GENERAL:
                border_configs[strategy] = {
                    'border_thickness': self.configs[strategy]['border_thickness']
                }
        
        return {
            'border_configs': border_configs
        }
    
    def clear_caches(self) -> None:
        """Clear all caches to free memory."""
        if self.template_cache:
            self.template_cache.clear()
        if self.preprocessing_cache:
            self.preprocessing_cache.clear()
        logger = self.logger
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
