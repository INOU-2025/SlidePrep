"""
Shared template matching utilities for line detection.

This module provides common functions for template-based line detection
used across different processing scripts.
"""

import cv2
import numpy as np
import os
from typing import List, Tuple, Optional
from glob import glob


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


def draw_classified_contours(base_image: np.ndarray, contours: List[np.ndarray], 
                           template_shape: Tuple[int, int], orientation: str, 
                           border_thickness: int, min_area: int = 100) -> np.ndarray:
    """
    Draw contours with classification-based coloring.
    
    Args:
        base_image: Base image to draw on
        contours: List of contours to draw
        template_shape: Shape of template used for detection
        orientation: 'horizontal' or 'vertical'
        border_thickness: Border zone thickness
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

        is_valid = contour_fully_within_zone(box, (h, w), border_thickness, orientation)

        # Color coding: green for valid vertical, blue for valid horizontal, red for invalid
        color = (0, 255, 0) if orientation == 'vertical' else (255, 0, 0)
        if not is_valid:
            color = (0, 0, 255)  # red for invalid

        cv2.drawContours(result, [box], 0, color, 2)
    
    return result


def draw_all_contours(base_image: np.ndarray, contours: List[np.ndarray], 
                     template_shape: Tuple[int, int], orientation: str, 
                     min_area: int = 100) -> np.ndarray:
    """
    Draw all contours without border zone restrictions.
    
    Args:
        base_image: Base image to draw on
        contours: List of contours to draw
        template_shape: Shape of template used for detection
        orientation: 'horizontal' or 'vertical'
        min_area: Minimum contour area to draw
    
    Returns:
        Image with drawn contours
    """
    result = base_image.copy()
    if len(result.shape) == 2:
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
    
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

        # Color coding: green for vertical, blue for horizontal (all valid)
        color = (0, 255, 0) if orientation == 'vertical' else (255, 0, 0)
        cv2.drawContours(result, [box], 0, color, 2)
    
    return result


class GeneralLineDetector:
    """
    General template-based line detector without border zone restrictions.
    Accepts all detections regardless of position.
    """
    
    def __init__(self, template_length: int = 300, thickness: int = 20, 
                 angles: List[float] = None, threshold: float = 0.1, 
                 min_contour_area: int = 100):
        """
        Initialize general detector with parameters.
        
        Args:
            template_length: Length of line templates
            thickness: Thickness of line templates
            angles: List of angles to test (default: [+2, -2])
            threshold: Detection threshold
            min_contour_area: Minimum contour area for detection
        """
        self.template_length = template_length
        self.thickness = thickness
        self.angles = angles if angles is not None else [2, -2]
        self.threshold = threshold
        self.min_contour_area = min_contour_area
        
        # Pre-generate templates
        self.h_templates = [generate_blurred_template(template_length, thickness, a, 'horizontal') 
                           for a in self.angles]
        self.v_templates = [generate_blurred_template(template_length, thickness, a, 'vertical') 
                           for a in self.angles]
    
    def detect_lines(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray], List[np.ndarray]]:
        """
        Detect horizontal and vertical lines in image.
        
        Args:
            image: Input grayscale image
        
        Returns:
            Tuple of (h_mask, v_mask, h_contours, v_contours)
        """
        inverted = cv2.bitwise_not(image)
        
        # Perform template matching
        h_map = perform_template_matching(inverted, self.h_templates)
        v_map = perform_template_matching(inverted, self.v_templates)
        
        # Create detection masks
        h_mask = create_detection_mask(h_map, self.threshold)
        v_mask = create_detection_mask(v_map, self.threshold)
        
        # Find contours
        h_contours, _ = cv2.findContours(h_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        v_contours, _ = cv2.findContours(v_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return h_mask, v_mask, h_contours, v_contours
    
    def create_visualization(self, image: np.ndarray, h_contours: List[np.ndarray], 
                           v_contours: List[np.ndarray]) -> np.ndarray:
        """
        Create visualization with all detected lines (no border restrictions).
        
        Args:
            image: Input grayscale image
            h_contours: Horizontal line contours
            v_contours: Vertical line contours
        
        Returns:
            Visualization image
        """
        # Convert to BGR (no border overlay for general detection)
        base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        
        # Draw all contours without border filtering
        base = draw_all_contours(base, h_contours, self.h_templates[0].shape, 
                               'horizontal', self.min_contour_area)
        base = draw_all_contours(base, v_contours, self.v_templates[0].shape, 
                               'vertical', self.min_contour_area)
        
        return base


class TemplateLineDetector:
    """
    Template-based line detector with configurable border zone restrictions.
    """
    
    def __init__(self, template_length: int = 100, thickness: int = 7, 
                 angles: List[float] = None, border_thickness: int = 35, 
                 threshold: float = 0.1, min_contour_area: int = 100):
        """
        Initialize detector with parameters.
        
        Args:
            template_length: Length of line templates
            thickness: Thickness of line templates
            angles: List of angles to test (default: [+2, -2])
            border_thickness: Border zone thickness
            threshold: Detection threshold
            min_contour_area: Minimum contour area for detection
        """
        self.template_length = template_length
        self.thickness = thickness
        self.angles = angles if angles is not None else [2, -2]
        self.border_thickness = border_thickness
        self.threshold = threshold
        self.min_contour_area = min_contour_area
        
        # Pre-generate templates
        self.h_templates = [generate_blurred_template(template_length, thickness, a, 'horizontal') 
                           for a in self.angles]
        self.v_templates = [generate_blurred_template(template_length, thickness, a, 'vertical') 
                           for a in self.angles]
    
    def detect_lines(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray], List[np.ndarray]]:
        """
        Detect horizontal and vertical lines in image.
        
        Args:
            image: Input grayscale image
        
        Returns:
            Tuple of (h_mask, v_mask, h_contours, v_contours)
        """
        inverted = cv2.bitwise_not(image)
        
        # Perform template matching
        h_map = perform_template_matching(inverted, self.h_templates)
        v_map = perform_template_matching(inverted, self.v_templates)
        
        # Create detection masks
        h_mask = create_detection_mask(h_map, self.threshold)
        v_mask = create_detection_mask(v_map, self.threshold)
        
        # Find contours
        h_contours, _ = cv2.findContours(h_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        v_contours, _ = cv2.findContours(v_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return h_mask, v_mask, h_contours, v_contours
    
    def create_visualization(self, image: np.ndarray, h_contours: List[np.ndarray], 
                           v_contours: List[np.ndarray]) -> np.ndarray:
        """
        Create visualization with detected lines and border overlay.
        
        Args:
            image: Input grayscale image
            h_contours: Horizontal line contours
            v_contours: Vertical line contours
        
        Returns:
            Visualization image
        """
        # Convert to BGR and add border overlay
        base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        base = draw_border_overlay(base, self.border_thickness)
        
        # Draw contours with border zone filtering
        base = draw_classified_contours(base, h_contours, self.h_templates[0].shape, 
                                      'horizontal', self.border_thickness, self.min_contour_area)
        base = draw_classified_contours(base, v_contours, self.v_templates[0].shape, 
                                      'vertical', self.border_thickness, self.min_contour_area)
        
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
