"""
Adaptive line detection debug drawer.

Provides visualization capabilities for the AdaptiveLineDetector results.
"""

import cv2
import numpy as np
from typing import Any, Optional, Dict, List, Tuple
from utils.debug.base_drawer import BaseDrawer
from utils.detection.models import DetectionStrategy
from utils.detection.contour_analysis import contour_fully_within_zone


class AdaptiveDetectionDrawer(BaseDrawer):
    """
    Debug drawer for adaptive line detection visualization.

    Creates comprehensive visualizations showing:
    - Detection results with strategy-specific coloring
    - Border zone overlays when applicable
    - Strategy information overlay
    - Cache statistics overlay
    """

    def __init__(self, show_strategy_info: bool = True, show_cache_stats: bool = True,
                 show_border_zones: bool = True):
        """
        Initialize the adaptive detection drawer.

        Args:
            show_strategy_info: Whether to overlay strategy information
            show_cache_stats: Whether to overlay cache statistics
            show_border_zones: Whether to show border zone overlays
        """
        self.show_strategy_info = show_strategy_info
        self.show_cache_stats = show_cache_stats
        self.show_border_zones = show_border_zones

    def draw(self, image: np.ndarray, results: Any = None, metadata: Any = None) -> Optional[np.ndarray]:
        """
        Draw adaptive detection results on the image.

        Args:
            image: Base grayscale image
            results: Detection results from AdaptiveLineDetector.detect_lines()
            metadata: Additional metadata (detector instance, timing info, etc.)

        Returns:
            Image with drawn visualizations
        """
        if results is None:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        # Convert to BGR for visualization
        base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        detections = results.get('detections', {})
        strategies = results.get('strategies', {})
        cache_stats = results.get('cache_stats', {})

        # Get detector configurations (from metadata if available)
        detector = metadata.get('detector') if metadata else None
        configs = detector.configs if detector else self._get_default_configs()

        # Draw border overlay if any border strategy was used
        if self.show_border_zones:
            max_border_thickness = 0
            for orientation, strategy in strategies.items():
                if strategy in [DetectionStrategy.THICK_BORDER, DetectionStrategy.THIN_BORDER]:
                    config = configs[strategy]
                    max_border_thickness = max(
                        max_border_thickness, config['border_thickness'])

            if max_border_thickness > 0:
                base = self._draw_border_overlay(
                    base, max_border_thickness, alpha=0.15)

        # Draw detections for each orientation
        for orientation, (mask, contours) in detections.items():
            if contours and strategies.get(orientation):
                strategy = strategies[orientation]
                config = configs[strategy]

                min_area = detector.min_contour_area if detector else 100

                base = self._draw_contours_with_strategy(
                    base, contours, orientation, strategy, 
                    config.get('border_thickness', 0), min_area
                )

        # Add strategy information overlay
        if self.show_strategy_info:
            base = self._add_strategy_overlay(
                base, strategies, detections, detector)

        # Add cache statistics overlay
        if self.show_cache_stats and cache_stats:
            base = self._add_cache_overlay(base, cache_stats)

        return base

    def _draw_border_overlay(self, image: np.ndarray, border_thickness: int, alpha: float = 0.25) -> np.ndarray:
        """
        Draw border zone overlay on image.

        Args:
            image: Input image
            border_thickness: Border zone thickness
            alpha: Overlay transparency (0-1)

        Returns:
            Image with border overlay
        """
        h, w = image.shape[:2]
        overlay = image.copy()

        # Ensure overlay is BGR
        if len(overlay.shape) == 2:
            overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)

        cv2.rectangle(overlay, (0, 0), (w, border_thickness), (0, 0, 255), -1)
        cv2.rectangle(overlay, (0, h - border_thickness),
                      (w, h), (0, 0, 255), -1)
        cv2.rectangle(overlay, (0, 0), (border_thickness, h), (0, 0, 255), -1)
        cv2.rectangle(overlay, (w - border_thickness, 0),
                      (w, h), (0, 0, 255), -1)

        # Ensure base image is BGR for blending
        base = image.copy()
        if len(base.shape) == 2:
            base = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)

        return cv2.addWeighted(overlay, alpha, base, 1 - alpha, 0)

    def _draw_contours_with_strategy(self, base_image: np.ndarray, contours: List[np.ndarray],
                                     orientation: str, strategy: DetectionStrategy, 
                                     border_thickness: int = 0, min_area: int = 100) -> np.ndarray:
        """
        Draw contours with strategy-specific coloring and filtering.
        
        Note: Contours are pre-corrected by the detector, so no offset calculation needed.

        Args:
            base_image: Base image to draw on
            contours: List of pre-corrected contours to draw
            orientation: 'horizontal' or 'vertical'
            strategy: Detection strategy used
            border_thickness: Border zone thickness (for border strategies)
            min_area: Minimum contour area to draw

        Returns:
            Image with drawn contours
        """
        result = base_image.copy()
        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        h, w = result.shape[:2]

        for cnt in contours:
            if cv2.contourArea(cnt) < min_area:
                continue

            # Contours are already offset-corrected by the detector
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.intp(box)

            # For general strategy, accept all contours
            if strategy == DetectionStrategy.GENERAL:
                is_valid = True
            else:
                # For border strategies, check border zone
                is_valid = contour_fully_within_zone(
                    box, (h, w), border_thickness, orientation)

            # Color coding based on strategy and validity
            if strategy == DetectionStrategy.GENERAL:
                # Bright colors for general detection
                color = (0, 255, 0) if orientation == 'vertical' else (255, 0, 0)
            elif strategy == DetectionStrategy.THICK_BORDER:
                # Medium colors for thick border
                color = (0, 200, 0) if orientation == 'vertical' else (200, 0, 0)
            else:  # THIN_BORDER
                # Darker colors for thin border
                color = (0, 150, 0) if orientation == 'vertical' else (150, 0, 0)

            if not is_valid:
                color = (0, 0, 255)  # red for invalid

            cv2.drawContours(result, [box], 0, color, 2)

        return result

    def _get_default_configs(self) -> Dict[DetectionStrategy, Dict[str, Any]]:
        """Get default configurations if detector is not available."""
        return {
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

    def _add_strategy_overlay(self, image: np.ndarray, strategies: Dict[str, DetectionStrategy],
                              detections: Dict[str, tuple], detector) -> np.ndarray:
        """Add strategy information overlay to the image."""
        h, w = image.shape[:2]
        min_area = detector.min_contour_area if detector else 100

        # Create semi-transparent overlay
        overlay = image.copy()

        # Strategy info box
        box_height = 120
        box_width = 280
        y_start = 10
        x_start = 10

        # Draw background box
        cv2.rectangle(overlay, (x_start, y_start),
                      (x_start + box_width, y_start + box_height),
                      (0, 0, 0), -1)

        # Add strategy information
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        color = (255, 255, 255)

        y_offset = y_start + 20
        cv2.putText(overlay, "Detection Strategies:",
                    (x_start + 5, y_offset), font, font_scale, color, thickness)

        y_offset += 20
        for orientation in ['horizontal', 'vertical']:
            strategy = strategies.get(orientation)
            if strategy:
                mask, contours = detections[orientation]
                valid_count = len(
                    [c for c in contours if cv2.contourArea(c) >= min_area])

                # Strategy-specific color
                if strategy == DetectionStrategy.GENERAL:
                    strategy_color = (
                        0, 255, 0) if orientation == 'vertical' else (255, 0, 0)
                elif strategy == DetectionStrategy.THICK_BORDER:
                    strategy_color = (
                        0, 200, 0) if orientation == 'vertical' else (200, 0, 0)
                else:  # THIN_BORDER
                    strategy_color = (
                        0, 150, 0) if orientation == 'vertical' else (150, 0, 0)

                text = f"{orientation}: {valid_count} ({strategy.value})"
                cv2.putText(overlay, text, (x_start + 5, y_offset),
                            font, font_scale, strategy_color, thickness)
            else:
                cv2.putText(overlay, f"{orientation}: Not found",
                            (x_start + 5, y_offset), font, font_scale, (0, 0, 255), thickness)
            y_offset += 20

        # Blend overlay
        cv2.addWeighted(overlay, 0.8, image, 0.2, 0, image)
        return image

    def _add_cache_overlay(self, image: np.ndarray, cache_stats: Dict[str, int]) -> np.ndarray:
        """Add cache statistics overlay to the image."""
        h, w = image.shape[:2]

        # Cache info box (top right)
        box_height = 80
        box_width = 200
        y_start = 10
        x_start = w - box_width - 10

        # Create semi-transparent overlay
        overlay = image.copy()

        # Draw background box
        cv2.rectangle(overlay, (x_start, y_start),
                      (x_start + box_width, y_start + box_height),
                      (0, 0, 0), -1)

        # Add cache statistics
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.4
        thickness = 1
        color = (255, 255, 255)

        y_offset = y_start + 15
        cv2.putText(overlay, "Cache Statistics:",
                    (x_start + 5, y_offset), font, font_scale, color, thickness)

        # Template cache
        y_offset += 15
        template_hits = cache_stats.get('template_cache_hits', 0)
        template_misses = cache_stats.get('template_cache_misses', 0)
        template_total = template_hits + template_misses
        template_rate = f"{template_hits}/{template_total}" if template_total > 0 else "0/0"
        cv2.putText(overlay, f"Template: {template_rate}",
                    (x_start + 5, y_offset), font, font_scale, (0, 255, 255), thickness)

        # Preprocessing cache
        y_offset += 15
        preprocessing_hits = cache_stats.get('preprocessing_cache_hits', 0)
        preprocessing_misses = cache_stats.get('preprocessing_cache_misses', 0)
        preprocessing_total = preprocessing_hits + preprocessing_misses
        preprocessing_rate = f"{preprocessing_hits}/{preprocessing_total}" if preprocessing_total > 0 else "0/0"
        cv2.putText(overlay, f"Preproc: {preprocessing_rate}",
                    (x_start + 5, y_offset), font, font_scale, (255, 255, 0), thickness)

        # Cache efficiency
        y_offset += 15
        if template_total > 0:
            efficiency = (template_hits / template_total) * 100
            cv2.putText(overlay, f"Efficiency: {efficiency:.1f}%",
                        (x_start + 5, y_offset), font, font_scale, (0, 255, 0), thickness)

        # Blend overlay
        cv2.addWeighted(overlay, 0.8, image, 0.2, 0, image)
        return image
