"""
Binarization Utilities Module

This module contains various binarization methods that were evaluated during development.
While the production system uses Combined Differential method, these utilities preserve
all the alternative approaches for research, experimentation, and special use cases.

Available Methods:
- Global thresholding (fixed and adaptive)
- Otsu automatic thresholding  
- Adaptive thresholding (mean and gaussian)
- Multi-Otsu thresholding
- Line-enhanced thresholding
- Morphological operations
- Combined differential (production method)

Usage:
    from utils.binarization_methods import BinarizationMethods
    
    methods = BinarizationMethods()
    binary_image = methods.apply_otsu(gray_image)
    binary_image = methods.apply_multi_otsu(gray_image)
    # etc.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any
from enum import Enum


class ThresholdMethod(Enum):
    """Enumeration of available binarization methods."""
    GLOBAL = "global"
    OTSU = "otsu" 
    ADAPTIVE = "adaptive"
    MULTI_OTSU = "multi_otsu"
    LINE_ENHANCED = "line_enhanced"
    MORPHOLOGICAL = "morphological"
    COMBINED_DIFFERENTIAL = "combined_differential"


class BinarizationMethods:
    """
    Collection of binarization methods for image processing.
    
    This class provides access to various thresholding techniques that can be
    used for different types of images and analysis requirements.
    """
    
    def __init__(self, debug_callback: Optional[callable] = None):
        """
        Initialize the binarization methods utility.
        
        Args:
            debug_callback: Optional function to call for debug messages
        """
        self.debug_callback = debug_callback
        
    def debug(self, message: str) -> None:
        """Send debug message to callback if available."""
        if self.debug_callback:
            self.debug_callback(message)
            
    def apply_method(self, method: ThresholdMethod, gray: np.ndarray, **kwargs) -> np.ndarray:
        """
        Apply a specific binarization method.
        
        Args:
            method: The ThresholdMethod to apply
            gray: Input grayscale image
            **kwargs: Method-specific parameters
            
        Returns:
            Binary image (0=foreground/black, 255=background/white)
        """
        method_map = {
            ThresholdMethod.GLOBAL: self.apply_global_threshold,
            ThresholdMethod.OTSU: self.apply_otsu_threshold,
            ThresholdMethod.ADAPTIVE: self.apply_adaptive_threshold,
            ThresholdMethod.MULTI_OTSU: self.apply_multi_otsu_threshold,
            ThresholdMethod.LINE_ENHANCED: self.apply_line_enhanced_threshold,
            ThresholdMethod.MORPHOLOGICAL: self.apply_morphological_threshold,
            ThresholdMethod.COMBINED_DIFFERENTIAL: self.apply_combined_differential_threshold,
        }
        
        if method not in method_map:
            raise ValueError(f"Unknown threshold method: {method}")
            
        return method_map[method](gray, **kwargs)
    
    def apply_global_threshold(self, gray: np.ndarray, threshold: int = 127, invert: bool = False) -> np.ndarray:
        """
        Apply global (fixed) thresholding.
        
        Args:
            gray: Input grayscale image
            threshold: Fixed threshold value (0-255)
            invert: If True, dark regions become background
            
        Returns:
            Binary image
        """
        thresh_type = cv2.THRESH_BINARY_INV if not invert else cv2.THRESH_BINARY
        _, binary = cv2.threshold(gray, threshold, 255, thresh_type)
        
        self.debug(f"Applied global threshold: {threshold} ({'inverted' if invert else 'normal'})")
        return binary
    
    def apply_otsu_threshold(self, gray: np.ndarray, invert: bool = False) -> np.ndarray:
        """
        Apply Otsu's automatic thresholding.
        
        Args:
            gray: Input grayscale image
            invert: If True, dark regions become background
            
        Returns:
            Binary image
        """
        thresh_type = cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU if not invert else cv2.THRESH_BINARY + cv2.THRESH_OTSU
        threshold_value, binary = cv2.threshold(gray, 0, 255, thresh_type)
        
        self.debug(f"Applied Otsu threshold: computed threshold={threshold_value:.2f} ({'inverted' if invert else 'normal'})")
        return binary
    
    def apply_adaptive_threshold(self, gray: np.ndarray, method: str = "gaussian", 
                               thresh_type: str = "binary", block_size: int = 11, 
                               c_constant: float = 2, invert: bool = False) -> np.ndarray:
        """
        Apply adaptive thresholding.
        
        Args:
            gray: Input grayscale image
            method: "mean" or "gaussian"
            thresh_type: "binary" or "binary_inv"
            block_size: Size of neighborhood for threshold calculation
            c_constant: Constant subtracted from mean/weighted mean
            invert: If True, apply additional inversion
            
        Returns:
            Binary image
        """
        # Map method names
        adaptive_method = cv2.ADAPTIVE_THRESH_MEAN_C if method == "mean" else cv2.ADAPTIVE_THRESH_GAUSSIAN_C
        
        # Map threshold types
        if thresh_type == "binary_inv":
            threshold_type = cv2.THRESH_BINARY_INV
        else:
            threshold_type = cv2.THRESH_BINARY
            
        binary = cv2.adaptiveThreshold(gray, 255, adaptive_method, threshold_type, block_size, c_constant)
        
        if invert:
            binary = cv2.bitwise_not(binary)
            
        self.debug(f"Applied adaptive threshold: {method}, block_size={block_size}, C={c_constant}")
        return binary
    
    def apply_multi_otsu_threshold(self, gray: np.ndarray, classes: int = 3, invert: bool = False) -> np.ndarray:
        """
        Apply multi-level Otsu thresholding.
        
        Args:
            gray: Input grayscale image
            classes: Number of threshold classes
            invert: If True, dark regions become background
            
        Returns:
            Binary image
        """
        try:
            from skimage.filters import threshold_multiotsu
            
            # Compute multi-level thresholds
            thresholds = threshold_multiotsu(gray, classes=classes)
            
            # Create binary image where darkest regions are foreground
            if not invert:
                # Dark regions (grid lines) become BLACK on WHITE background
                binary = np.ones_like(gray) * 255  # Start with WHITE background
                binary[gray <= thresholds[0]] = 0  # Darkest regions become BLACK
            else:
                # Dark regions become WHITE on BLACK background
                binary = np.zeros_like(gray)  # Start with BLACK background
                binary[gray <= thresholds[0]] = 255  # Darkest regions become WHITE
            
            self.debug(f"Applied multi-Otsu thresholds: {[f'{t:.1f}' for t in thresholds]} ({'inverted' if invert else 'normal'})")
            return binary
            
        except ImportError:
            self.debug("scikit-image not available, falling back to regular Otsu")
            return self.apply_otsu_threshold(gray, invert=invert)
    
    def apply_line_enhanced_threshold(self, gray: np.ndarray, kernel_length: int = 21, 
                                    rotation_angle: float = 2.0, invert: bool = False) -> np.ndarray:
        """
        Apply line-enhanced thresholding for detecting linear structures.
        
        Args:
            gray: Input grayscale image
            kernel_length: Length of line detection kernel
            rotation_angle: Rotation angle in degrees
            invert: If True, dark regions become background
            
        Returns:
            Binary image
        """
        # Create rotated line kernels
        angle_rad = np.radians(rotation_angle)
        
        # Horizontal kernel (rotated)
        h_kernel = np.zeros((kernel_length, kernel_length), dtype=np.float32)
        center = kernel_length // 2
        for i in range(kernel_length):
            x = i - center
            y = int(x * np.tan(angle_rad))
            if abs(y) <= center:
                h_kernel[center + y, i] = 1
        h_kernel /= np.sum(h_kernel)
        
        # Vertical kernel (rotated)
        v_kernel = np.zeros((kernel_length, kernel_length), dtype=np.float32)
        for i in range(kernel_length):
            y = i - center
            x = int(y * np.tan(angle_rad))
            if abs(x) <= center:
                v_kernel[i, center + x] = 1
        v_kernel /= np.sum(v_kernel)
        
        # Apply line detection
        h_response = cv2.filter2D(gray, -1, h_kernel)
        v_response = cv2.filter2D(gray, -1, v_kernel)
        
        # Combine responses
        line_enhanced = cv2.max(h_response, v_response)
        
        # Apply Otsu to the enhanced image
        thresh_type = cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU if not invert else cv2.THRESH_BINARY + cv2.THRESH_OTSU
        threshold_value, binary = cv2.threshold(line_enhanced, 0, 255, thresh_type)
        
        self.debug(f"Applied line-enhanced threshold: kernel={kernel_length}, angle={rotation_angle}°, threshold={threshold_value:.2f}")
        return binary
    
    def apply_morphological_threshold(self, gray: np.ndarray, operation: str = "close", 
                                    kernel_size: int = 3, invert: bool = False) -> np.ndarray:
        """
        Apply morphological operations after Otsu thresholding.
        
        Args:
            gray: Input grayscale image
            operation: "open", "close", "gradient", "tophat", "blackhat"
            kernel_size: Size of morphological kernel
            invert: If True, dark regions become background
            
        Returns:
            Binary image
        """
        # First apply Otsu
        binary = self.apply_otsu_threshold(gray, invert=invert)
        
        # Create morphological kernel
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        
        # Apply morphological operation
        operation_map = {
            "open": cv2.MORPH_OPEN,
            "close": cv2.MORPH_CLOSE,
            "gradient": cv2.MORPH_GRADIENT,
            "tophat": cv2.MORPH_TOPHAT,
            "blackhat": cv2.MORPH_BLACKHAT
        }
        
        if operation not in operation_map:
            raise ValueError(f"Unknown morphological operation: {operation}")
            
        morph_op = operation_map[operation]
        result = cv2.morphologyEx(binary, morph_op, kernel)
        
        self.debug(f"Applied morphological {operation}: kernel_size={kernel_size}")
        return result
    
    def apply_combined_differential_threshold(self, gray: np.ndarray) -> np.ndarray:
        """
        Apply combined differential thresholding (production method).
        
        This combines multi-Otsu thresholding with spurious element removal
        to achieve high-quality grid preservation while removing cellular content.
        
        Args:
            gray: Input grayscale image
            
        Returns:
            Binary image
        """
        self.debug("Applying combined differential threshold (multi_otsu - spurious elements)")
        
        # STEP 1: Get multi_otsu result
        multi_otsu_result = self.apply_multi_otsu_threshold(gray)
        
        # Apply polarity correction to multi_otsu result
        total_black = np.sum(multi_otsu_result == 0)
        total_white = np.sum(multi_otsu_result == 255)
        if total_black > total_white:
            multi_otsu_result = cv2.bitwise_not(multi_otsu_result)
            self.debug("Applied polarity correction to multi_otsu")
        
        # STEP 2: Create spurious element detector
        spurious_elements = self._detect_spurious_elements(gray, multi_otsu_result)
        
        # STEP 3: Remove spurious elements from multi_otsu result
        multi_otsu_fg = multi_otsu_result == 0  # BLACK pixels are foreground
        spurious_fg = spurious_elements == 0    # BLACK pixels are spurious
        
        # Remove spurious elements: keep multi_otsu BUT remove spurious areas
        clean_foreground = multi_otsu_fg & ~spurious_fg  # multi_otsu AND NOT spurious
        
        # Convert back to standard binary format
        final_binary = np.where(clean_foreground, 0, 255).astype(np.uint8)
        
        self.debug(f"Multi-otsu foreground pixels: {np.sum(multi_otsu_fg)}")
        self.debug(f"Spurious element pixels: {np.sum(spurious_fg)}")
        self.debug(f"Clean foreground pixels: {np.sum(clean_foreground)}")
        
        return final_binary
    
    def _detect_spurious_elements(self, gray: np.ndarray, multi_otsu_result: np.ndarray) -> np.ndarray:
        """
        Detect spurious elements (likely cellular content) to remove from grid detection.
        
        Production parameters optimized for thick grid detection.
        """
        spurious_mask = np.zeros_like(gray, dtype=np.uint8)
        
        # Production parameters
        min_spurious_area = 300    # Ignore smaller noise elements
        max_spurious_area = 1500   # Target cellular-sized objects  
        max_aspect_ratio = 1.5     # Circular/oval objects only
        connectivity = 8           # 8-connectivity for better component detection
        
        # Find connected components in multi_otsu result
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            cv2.bitwise_not(multi_otsu_result), connectivity=connectivity)
        
        # Analyze each component to determine if it's spurious
        for i in range(1, num_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            bbox_width = stats[i, cv2.CC_STAT_WIDTH]
            bbox_height = stats[i, cv2.CC_STAT_HEIGHT]
            
            # Calculate aspect ratio
            aspect_ratio = max(bbox_width, bbox_height) / max(min(bbox_width, bbox_height), 1)
            
            # Apply criteria for spurious elements
            is_spurious = (
                min_spurious_area <= area <= max_spurious_area and
                aspect_ratio <= max_aspect_ratio
            )
            
            if is_spurious:
                # Mark this component as spurious
                component_mask = (labels == i).astype(np.uint8) * 255
                spurious_mask = cv2.bitwise_or(spurious_mask, component_mask)
        
        # Convert to binary format: BLACK = spurious elements, WHITE = background
        spurious_binary = cv2.bitwise_not(spurious_mask)
        
        self.debug(f"Detected spurious elements: {np.sum(spurious_binary == 0)} pixels")
        return spurious_binary
    
    def get_available_methods(self) -> list:
        """Get list of available binarization methods."""
        return [method.value for method in ThresholdMethod]
    
    def get_method_info(self, method: ThresholdMethod) -> Dict[str, Any]:
        """
        Get information about a specific method.
        
        Returns:
            Dictionary with method description and parameters
        """
        method_info = {
            ThresholdMethod.GLOBAL: {
                "description": "Fixed threshold value",
                "parameters": ["threshold", "invert"],
                "use_case": "Simple binary separation with known threshold"
            },
            ThresholdMethod.OTSU: {
                "description": "Automatic threshold selection using Otsu's method",
                "parameters": ["invert"],
                "use_case": "Bimodal intensity distributions"
            },
            ThresholdMethod.ADAPTIVE: {
                "description": "Local threshold based on neighborhood statistics",
                "parameters": ["method", "thresh_type", "block_size", "c_constant", "invert"],
                "use_case": "Varying illumination conditions"
            },
            ThresholdMethod.MULTI_OTSU: {
                "description": "Multi-level Otsu for multiple intensity classes",
                "parameters": ["classes", "invert"],
                "use_case": "Images with multiple intensity regions"
            },
            ThresholdMethod.LINE_ENHANCED: {
                "description": "Enhanced detection of linear structures",
                "parameters": ["kernel_length", "rotation_angle", "invert"],
                "use_case": "Grid lines and linear patterns"
            },
            ThresholdMethod.MORPHOLOGICAL: {
                "description": "Otsu followed by morphological operations",
                "parameters": ["operation", "kernel_size", "invert"],
                "use_case": "Noise reduction and shape refinement"
            },
            ThresholdMethod.COMBINED_DIFFERENTIAL: {
                "description": "Production method: Multi-Otsu with spurious element removal",
                "parameters": [],
                "use_case": "Thick grid detection with cellular content removal"
            }
        }
        
        return method_info.get(method, {"description": "Unknown method", "parameters": [], "use_case": "Unknown"})
