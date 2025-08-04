"""
Shared template matching utilities for line detection.

This module provides common functions for template-based line detection
used across different processing scripts.
"""

import cv2
import numpy as np
import os
import hashlib
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
from glob import glob


class DetectionStrategy(Enum):
    """Detection strategy types."""
    GENERAL = "general"
    THICK_BORDER = "thick_border"
    THIN_BORDER = "thin_border"


def generate_blurred_template(length: int, thickness: int, angle_deg: float, orientation: str) -> np.ndarray:
    """
    Generate a blurred template for line detection.
    
    Args:
        length: Template length in pixels
        thickness: Template thickness in pixels
        angle_deg: Rotation angle in degrees
        orientation: 'horizontal' or 'vertical'
    
    Returns:
        Blurred template as numpy array
    """
    if orientation == 'horizontal':
        template = np.zeros((thickness, length), dtype=np.uint8)
        cv2.rectangle(template, (0, 0), (length-1, thickness-1), 255, -1)
    else:
        template = np.zeros((length, thickness), dtype=np.uint8)
        cv2.rectangle(template, (0, 0), (thickness-1, length-1), 255, -1)
    
    template = cv2.GaussianBlur(template, (5, 5), 0)
    
    if angle_deg != 0:
        center = (template.shape[1] // 2, template.shape[0] // 2)
        M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
        template = cv2.warpAffine(template, M, (template.shape[1], template.shape[0]), 
                                 flags=cv2.INTER_LINEAR, borderValue=0)
    return template


def pad_response(response: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
    """
    Pad template matching response to target shape.
    
    Args:
        response: Template matching response
        target_shape: Target (height, width) shape
    
    Returns:
        Padded response array
    """
    pad_y = target_shape[0] - response.shape[0]
    pad_x = target_shape[1] - response.shape[1]
    return cv2.copyMakeBorder(response, 0, pad_y, 0, pad_x, cv2.BORDER_CONSTANT, value=1.0)


def perform_template_matching(image: np.ndarray, templates: List[np.ndarray]) -> np.ndarray:
    """
    Perform template matching with multiple templates and return minimum response.
    
    Args:
        image: Input image (should be inverted for line detection)
        templates: List of templates to match
    
    Returns:
        Combined minimum response map
    """
    responses = [pad_response(cv2.matchTemplate(image, tpl, cv2.TM_SQDIFF_NORMED), image.shape) 
                for tpl in templates]
    return np.minimum.reduce(responses)


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


def contour_fully_within_zone(box: np.ndarray, img_shape: Tuple[int, int], 
                             border_thickness: int, orientation: str) -> bool:
    """
    Check if a contour bounding box is fully within border zone.
    
    Args:
        box: Bounding box points
        img_shape: Image (height, width)
        border_thickness: Border zone thickness
        orientation: 'horizontal' or 'vertical'
    
    Returns:
        True if contour is fully within appropriate border zone
    """
    h, w = img_shape
    if orientation == 'horizontal':
        in_top = all(y < border_thickness for _, y in box)
        in_bottom = all(y >= h - border_thickness for _, y in box)
        return in_top or in_bottom
    elif orientation == 'vertical':
        in_left = all(x < border_thickness for x, _ in box)
        in_right = all(x >= w - border_thickness for x, _ in box)
        return in_left or in_right
    return False


def draw_border_overlay(image: np.ndarray, border_thickness: int, alpha: float = 0.25) -> np.ndarray:
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
    cv2.rectangle(overlay, (0, h - border_thickness), (w, h), (0, 0, 255), -1)
    cv2.rectangle(overlay, (0, 0), (border_thickness, h), (0, 0, 255), -1)
    cv2.rectangle(overlay, (w - border_thickness, 0), (w, h), (0, 0, 255), -1)
    
    # Ensure base image is BGR for blending
    base = image.copy()
    if len(base.shape) == 2:
        base = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
    
    return cv2.addWeighted(overlay, alpha, base, 1 - alpha, 0)


def draw_contours_with_strategy(base_image: np.ndarray, contours: List[np.ndarray], 
                               template_shape: Tuple[int, int], orientation: str, 
                               strategy: DetectionStrategy, border_thickness: int = 0,
                               min_area: int = 100) -> np.ndarray:
    """
    Draw contours with strategy-specific coloring and filtering.
    
    Args:
        base_image: Base image to draw on
        contours: List of contours to draw
        template_shape: Shape of template used for detection
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
    offset_x = template_shape[1] // 2
    offset_y = template_shape[0] // 2

    for cnt in contours:
        if cv2.contourArea(cnt) < min_area:
            continue
            
        rect = cv2.minAreaRect(cnt)
        center, size, angle = rect
        corrected_center = (center[0] + offset_x, center[1] + offset_y)
        corrected_rect = (corrected_center, size, angle)
        box = cv2.boxPoints(corrected_rect)
        box = np.intp(box)

        # For general strategy, accept all contours
        if strategy == DetectionStrategy.GENERAL:
            is_valid = True
        else:
            # For border strategies, check border zone
            is_valid = contour_fully_within_zone(box, (h, w), border_thickness, orientation)

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
                 enable_preprocessing_cache: bool = True):
        """
        Initialize adaptive detector with optimization options.
        
        Args:
            min_contour_area: Minimum contour area for valid detection
            verbose: Whether to print detection strategy information
            enable_early_exit: Whether to stop when both orientations found
            enable_template_cache: Whether to cache generated templates
            enable_preprocessing_cache: Whether to cache image preprocessing
        """
        self.min_contour_area = min_contour_area
        self.verbose = verbose
        self.enable_early_exit = enable_early_exit
        self.enable_template_cache = enable_template_cache
        self.enable_preprocessing_cache = enable_preprocessing_cache
        
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
        
        # Template cache: strategy -> orientation -> List[templates]
        self._template_cache: Dict[DetectionStrategy, Dict[str, List[np.ndarray]]] = {}
        
        # Image preprocessing cache: image_hash -> inverted_image
        self._preprocessing_cache: Dict[str, np.ndarray] = {}
        self._cache_max_size = 50  # Limit cache size to prevent memory issues
        
        # Storage for detection results
        self.detection_results = {}
        self.strategies_used = {}
        
        # Performance tracking
        self.cache_hits = {'template': 0, 'preprocessing': 0}
        self.cache_misses = {'template': 0, 'preprocessing': 0}
    
    def _get_image_hash(self, image: np.ndarray) -> str:
        """Generate hash for image caching."""
        return hashlib.md5(image.tobytes()).hexdigest()
    
    def _get_preprocessed_image(self, image: np.ndarray) -> np.ndarray:
        """Get preprocessed (inverted) image with caching."""
        if not self.enable_preprocessing_cache:
            return cv2.bitwise_not(image)
        
        img_hash = self._get_image_hash(image)
        
        if img_hash in self._preprocessing_cache:
            self.cache_hits['preprocessing'] += 1
            return self._preprocessing_cache[img_hash]
        
        self.cache_misses['preprocessing'] += 1
        inverted = cv2.bitwise_not(image)
        
        # Manage cache size
        if len(self._preprocessing_cache) >= self._cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._preprocessing_cache))
            del self._preprocessing_cache[oldest_key]
        
        self._preprocessing_cache[img_hash] = inverted
        return inverted
    
    def _get_templates(self, strategy: DetectionStrategy, orientation: str) -> List[np.ndarray]:
        """Get templates with caching."""
        if not self.enable_template_cache:
            config = self.configs[strategy]
            return [generate_blurred_template(
                config['template_length'], 
                config['thickness'], 
                angle, 
                orientation
            ) for angle in config['angles']]
        
        # Check cache
        if strategy in self._template_cache and orientation in self._template_cache[strategy]:
            self.cache_hits['template'] += 1
            return self._template_cache[strategy][orientation]
        
        self.cache_misses['template'] += 1
        
        # Generate templates
        config = self.configs[strategy]
        templates = [generate_blurred_template(
            config['template_length'], 
            config['thickness'], 
            angle, 
            orientation
        ) for angle in config['angles']]
        
        # Cache templates
        if strategy not in self._template_cache:
            self._template_cache[strategy] = {}
        self._template_cache[strategy][orientation] = templates
        
        return templates
    
    def _has_valid_detections(self, contours: List[np.ndarray]) -> bool:
        """Check if contours contain valid detections based on area."""
        return any(cv2.contourArea(cnt) >= self.min_contour_area for cnt in contours)
    
    def _detect_single_orientation(self, image: np.ndarray, strategy: DetectionStrategy, 
                                  orientation: str) -> Tuple[np.ndarray, List[np.ndarray]]:
        """
        Detect lines for a single orientation with a specific strategy.
        Uses cached preprocessing and templates for better performance.
        
        Args:
            image: Input grayscale image
            strategy: Detection strategy to use
            orientation: Orientation to detect ('horizontal' or 'vertical')
        
        Returns:
            Tuple of (mask, contours)
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
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours for border strategies
        if strategy != DetectionStrategy.GENERAL:
            filtered_contours = []
            h, w = image.shape
            for cnt in contours:
                if cv2.contourArea(cnt) < self.min_contour_area:
                    continue
                
                rect = cv2.minAreaRect(cnt)
                box = cv2.boxPoints(rect)
                box = np.intp(box)
                
                if contour_fully_within_zone(box, (h, w), config['border_thickness'], orientation):
                    filtered_contours.append(cnt)
            
            contours = filtered_contours
        
        return mask, contours
    
    def detect_lines(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Adaptively detect lines using multiple strategies as needed.
        
        Optimizations:
        - Early exit: Stop when both orientations are found
        - Only processes missing orientations in each round for efficiency
        - Uses template and preprocessing caches
        
        Args:
            image: Input grayscale image
        
        Returns:
            Dictionary containing detection results and metadata
        """
        self.detection_results = {}
        self.strategies_used = {}
        
        missing_orientations = ['horizontal', 'vertical']
        
        # Strategy 1: General detection
        if self.verbose:
            print("Trying general detection...")
        
        for orientation in missing_orientations[:]:  # Copy to modify during iteration
            if self.verbose:
                print(f"  Processing {orientation} orientation...")
            
            mask, contours = self._detect_single_orientation(image, DetectionStrategy.GENERAL, orientation)
            
            if self._has_valid_detections(contours):
                self.detection_results[orientation] = (mask, contours)
                self.strategies_used[orientation] = DetectionStrategy.GENERAL
                missing_orientations.remove(orientation)
                if self.verbose:
                    print(f"    ✓ Found {len([c for c in contours if cv2.contourArea(c) >= self.min_contour_area])} {orientation} lines")
            else:
                if self.verbose:
                    print(f"    ✗ No {orientation} lines found")
        
        # Early exit optimization: Stop if both orientations found
        if self.enable_early_exit and not missing_orientations:
            if self.verbose:
                print("✓ Early exit: Both orientations found in general detection")
            return self._create_result_dict(missing_orientations)
        
        # Strategy 2: Thick border detection for missing orientations only
        if missing_orientations:
            if self.verbose:
                print(f"Trying thick border detection for missing orientations: {missing_orientations}")
            
            for orientation in missing_orientations[:]:
                if self.verbose:
                    print(f"  Processing {orientation} orientation...")
                
                mask, contours = self._detect_single_orientation(image, DetectionStrategy.THICK_BORDER, orientation)
                
                if self._has_valid_detections(contours):
                    self.detection_results[orientation] = (mask, contours)
                    self.strategies_used[orientation] = DetectionStrategy.THICK_BORDER
                    missing_orientations.remove(orientation)
                    if self.verbose:
                        print(f"    ✓ Found {len([c for c in contours if cv2.contourArea(c) >= self.min_contour_area])} {orientation} lines")
                else:
                    if self.verbose:
                        print(f"    ✗ No {orientation} lines found")
        
        # Early exit optimization: Stop if both orientations found
        if self.enable_early_exit and not missing_orientations:
            if self.verbose:
                print("✓ Early exit: Both orientations found in thick border detection")
            return self._create_result_dict(missing_orientations)
        
        # Strategy 3: Thin border detection for still missing orientations only
        if missing_orientations:
            if self.verbose:
                print(f"Trying thin border detection for remaining orientations: {missing_orientations}")
            
            for orientation in missing_orientations[:]:
                if self.verbose:
                    print(f"  Processing {orientation} orientation...")
                
                mask, contours = self._detect_single_orientation(image, DetectionStrategy.THIN_BORDER, orientation)
                
                if self._has_valid_detections(contours):
                    self.detection_results[orientation] = (mask, contours)
                    self.strategies_used[orientation] = DetectionStrategy.THIN_BORDER
                    missing_orientations.remove(orientation)
                    if self.verbose:
                        print(f"    ✓ Found {len([c for c in contours if cv2.contourArea(c) >= self.min_contour_area])} {orientation} lines")
                else:
                    if self.verbose:
                        print(f"    ✗ No {orientation} lines found")
        
        return self._create_result_dict(missing_orientations)
    
    def _create_result_dict(self, missing_orientations: List[str]) -> Dict[str, Any]:
        """Create standardized result dictionary."""
        # Handle any still missing orientations
        if missing_orientations:
            if self.verbose:
                print(f"Final result: Could not find lines for {missing_orientations}")
            for orientation in missing_orientations:
                self.detection_results[orientation] = (np.zeros((100, 100), dtype=np.uint8), [])
                self.strategies_used[orientation] = None
        
        # Print final summary
        if self.verbose:
            print("\nDetection Summary:")
            for orientation in ['horizontal', 'vertical']:
                strategy = self.strategies_used.get(orientation)
                if strategy:
                    mask, contours = self.detection_results[orientation]
                    valid_count = len([c for c in contours if cv2.contourArea(c) >= self.min_contour_area])
                    print(f"  {orientation.capitalize()}: {valid_count} lines using {strategy.value}")
                else:
                    print(f"  {orientation.capitalize()}: No lines found")
            
            # Print cache performance
            print(f"\nCache Performance:")
            print(f"  Template cache - Hits: {self.cache_hits['template']}, Misses: {self.cache_misses['template']}")
            print(f"  Preprocessing cache - Hits: {self.cache_hits['preprocessing']}, Misses: {self.cache_misses['preprocessing']}")
        
        return {
            'detections': self.detection_results,
            'strategies': self.strategies_used,
            'missing': missing_orientations,
            'cache_stats': {
                'template_hits': self.cache_hits['template'],
                'template_misses': self.cache_misses['template'],
                'preprocessing_hits': self.cache_hits['preprocessing'],
                'preprocessing_misses': self.cache_misses['preprocessing']
            }
        }
    
    def clear_caches(self) -> None:
        """Clear all caches to free memory."""
        self._template_cache.clear()
        self._preprocessing_cache.clear()
        self.cache_hits = {'template': 0, 'preprocessing': 0}
        self.cache_misses = {'template': 0, 'preprocessing': 0}
        if self.verbose:
            print("Caches cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cache usage."""
        return {
            'template_cache_size': sum(len(orientations) for orientations in self._template_cache.values()),
            'preprocessing_cache_size': len(self._preprocessing_cache),
            'template_cache_hits': self.cache_hits['template'],
            'template_cache_misses': self.cache_misses['template'],
            'preprocessing_cache_hits': self.cache_hits['preprocessing'],
            'preprocessing_cache_misses': self.cache_misses['preprocessing']
        }
    
    def create_visualization(self, image: np.ndarray, detection_results: Dict[str, Any]) -> np.ndarray:
        """
        Create comprehensive visualization showing all detections with strategy indicators.
        
        Args:
            image: Input grayscale image
            detection_results: Results from detect_lines()
        
        Returns:
            Visualization image
        """
        base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        
        detections = detection_results['detections']
        strategies = detection_results['strategies']
        
        # Draw border overlay if any border strategy was used
        max_border_thickness = 0
        for orientation, strategy in strategies.items():
            if strategy in [DetectionStrategy.THICK_BORDER, DetectionStrategy.THIN_BORDER]:
                config = self.configs[strategy]
                max_border_thickness = max(max_border_thickness, config['border_thickness'])
        
        if max_border_thickness > 0:
            base = draw_border_overlay(base, max_border_thickness, alpha=0.15)
        
        # Draw detections for each orientation
        for orientation, (mask, contours) in detections.items():
            if contours and strategies[orientation]:
                strategy = strategies[orientation]
                config = self.configs[strategy]
                
                # Get template shape for offset calculation using cached templates
                templates = self._get_templates(strategy, orientation)
                template_shape = templates[0].shape if templates else (20, 300)
                
                base = draw_contours_with_strategy(
                    base, contours, template_shape, orientation, 
                    strategy, config['border_thickness'], self.min_contour_area
                )
        
        return base


# Keep the original classes for backward compatibility
class GeneralLineDetector:
    """General template-based line detector without border zone restrictions."""
    
    def __init__(self, template_length: int = 300, thickness: int = 20, 
                 angles: List[float] = None, threshold: float = 0.1, 
                 min_contour_area: int = 100):
        self.template_length = template_length
        self.thickness = thickness
        self.angles = angles if angles is not None else [2, -2]
        self.threshold = threshold
        self.min_contour_area = min_contour_area
        
        self.h_templates = [generate_blurred_template(template_length, thickness, a, 'horizontal') 
                           for a in self.angles]
        self.v_templates = [generate_blurred_template(template_length, thickness, a, 'vertical') 
                           for a in self.angles]
    
    def detect_lines(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray], List[np.ndarray]]:
        inverted = cv2.bitwise_not(image)
        h_map = perform_template_matching(inverted, self.h_templates)
        v_map = perform_template_matching(inverted, self.v_templates)
        h_mask = create_detection_mask(h_map, self.threshold)
        v_mask = create_detection_mask(v_map, self.threshold)
        h_contours, _ = cv2.findContours(h_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        v_contours, _ = cv2.findContours(v_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return h_mask, v_mask, h_contours, v_contours
    
    def create_visualization(self, image: np.ndarray, h_contours: List[np.ndarray], 
                           v_contours: List[np.ndarray]) -> np.ndarray:
        base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        base = draw_contours_with_strategy(base, h_contours, self.h_templates[0].shape, 
                                         'horizontal', DetectionStrategy.GENERAL, 0, self.min_contour_area)
        base = draw_contours_with_strategy(base, v_contours, self.v_templates[0].shape, 
                                         'vertical', DetectionStrategy.GENERAL, 0, self.min_contour_area)
        return base


class TemplateLineDetector:
    """Template-based line detector with configurable border zone restrictions."""
    
    def __init__(self, template_length: int = 100, thickness: int = 7, 
                 angles: List[float] = None, border_thickness: int = 35, 
                 threshold: float = 0.1, min_contour_area: int = 100):
        self.template_length = template_length
        self.thickness = thickness
        self.angles = angles if angles is not None else [2, -2]
        self.border_thickness = border_thickness
        self.threshold = threshold
        self.min_contour_area = min_contour_area
        
        self.h_templates = [generate_blurred_template(template_length, thickness, a, 'horizontal') 
                           for a in self.angles]
        self.v_templates = [generate_blurred_template(template_length, thickness, a, 'vertical') 
                           for a in self.angles]
    
    def detect_lines(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray], List[np.ndarray]]:
        inverted = cv2.bitwise_not(image)
        h_map = perform_template_matching(inverted, self.h_templates)
        v_map = perform_template_matching(inverted, self.v_templates)
        h_mask = create_detection_mask(h_map, self.threshold)
        v_mask = create_detection_mask(v_map, self.threshold)
        h_contours, _ = cv2.findContours(h_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        v_contours, _ = cv2.findContours(v_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return h_mask, v_mask, h_contours, v_contours
    
    def create_visualization(self, image: np.ndarray, h_contours: List[np.ndarray], 
                           v_contours: List[np.ndarray]) -> np.ndarray:
        base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        base = draw_border_overlay(base, self.border_thickness)
        
        strategy = DetectionStrategy.THICK_BORDER if self.border_thickness > 25 else DetectionStrategy.THIN_BORDER
        base = draw_contours_with_strategy(base, h_contours, self.h_templates[0].shape, 
                                         'horizontal', strategy, self.border_thickness, self.min_contour_area)
        base = draw_contours_with_strategy(base, v_contours, self.v_templates[0].shape, 
                                         'vertical', strategy, self.border_thickness, self.min_contour_area)
        return base


def process_image(path: str, out_dir: str, save_masks: bool = True, save_separate: bool = True, **kwargs) -> None:
    """
    Process single image with detailed output options.

    Args:
        path: Input image path
        out_dir: Output directory
        save_masks: Whether to save detection masks
        save_separate: Whether to save separate horizontal/vertical visualizations
        **kwargs: Parameters for TemplateLineDetector
    """
    name = os.path.splitext(os.path.basename(path))[0]
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"Could not read {path}")
        return

    # Create detector
    detector = TemplateLineDetector(**kwargs)

    # Detect lines
    h_mask, v_mask, h_contours, v_contours = detector.detect_lines(image)

    os.makedirs(out_dir, exist_ok=True)

    # Save masks if requested
    if save_masks:
        cv2.imwrite(os.path.join(out_dir, f"{name}_mask_h.png"), h_mask)
        cv2.imwrite(os.path.join(out_dir, f"{name}_mask_v.png"), v_mask)

    # Save separate visualizations if requested
    if save_separate:
        from utils.template_matching import draw_classified_contours

        base_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        rects_h = draw_classified_contours(base_bgr, h_contours, detector.h_templates[0].shape,
                                            'horizontal', detector.border_thickness)
        rects_v = draw_classified_contours(base_bgr, v_contours, detector.v_templates[0].shape,
                                            'vertical', detector.border_thickness)

        cv2.imwrite(os.path.join(out_dir, f"{name}_rects_h.png"), rects_h)
        cv2.imwrite(os.path.join(out_dir, f"{name}_rects_v.png"), rects_v)

    # Save combined visualization
    result = detector.create_visualization(image, h_contours, v_contours)
    cv2.imwrite(os.path.join(out_dir, f"{name}_combined.png"), result)


def process_batch(folder: str, out_dir: str, **kwargs) -> None:
    """
    Process batch of images with template matching.

    Args:
        folder: Input folder path
        out_dir: Output directory path
        **kwargs: Parameters for process_image and TemplateLineDetector
    """
    paths = glob(os.path.join(folder, "*.png"))
    for path in paths:
        print(f"Processing {path}")
        process_image(path, out_dir, **kwargs)


# Default configuration
DEFAULT_CONFIG = {
    'template_length': 300,
    'thickness': 20,
    'border_thickness': 100,
    'threshold': 0.1,
    'angles': [2, -2]
}


if __name__ == "__main__":
    # Example usage
    process_batch("input_images", "output_results", **DEFAULT_CONFIG)
