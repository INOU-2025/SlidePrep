"""Binarization utilities package."""

from enum import Enum
from typing import Optional, Callable, Dict, Any
import numpy as np

from .global_threshold import apply_global_threshold
from .otsu_threshold import apply_otsu_threshold
from .adaptive_threshold import apply_adaptive_threshold
from .multi_otsu import apply_multi_otsu_threshold
from .line_enhanced import apply_line_enhanced_threshold
from .morphological import apply_morphological_threshold
from .combined_differential import apply_combined_differential_threshold


__all__ = [
    "ThresholdMethod",
    "BinarizationMethods",
    "apply_global_threshold",
    "apply_otsu_threshold",
    "apply_adaptive_threshold",
    "apply_multi_otsu_threshold",
    "apply_line_enhanced_threshold",
    "apply_morphological_threshold",
    "apply_combined_differential_threshold",
]


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
    """Collection of binarization methods for image processing."""

    def __init__(self, debug_callback: Optional[Callable] = None) -> None:
        self.debug_callback = debug_callback

    def debug(self, message: str) -> None:
        if self.debug_callback:
            self.debug_callback(message)

    def apply_global_threshold(self, gray: np.ndarray, **kwargs) -> np.ndarray:
        return apply_global_threshold(gray, debug_callback=self.debug, **kwargs)

    def apply_otsu_threshold(self, gray: np.ndarray, **kwargs) -> np.ndarray:
        return apply_otsu_threshold(gray, debug_callback=self.debug, **kwargs)

    def apply_adaptive_threshold(self, gray: np.ndarray, **kwargs) -> np.ndarray:
        return apply_adaptive_threshold(gray, debug_callback=self.debug, **kwargs)

    def apply_multi_otsu_threshold(self, gray: np.ndarray, **kwargs) -> np.ndarray:
        return apply_multi_otsu_threshold(gray, debug_callback=self.debug, **kwargs)

    def apply_line_enhanced_threshold(self, gray: np.ndarray, **kwargs) -> np.ndarray:
        return apply_line_enhanced_threshold(gray, debug_callback=self.debug, **kwargs)

    def apply_morphological_threshold(self, gray: np.ndarray, **kwargs) -> np.ndarray:
        return apply_morphological_threshold(gray, debug_callback=self.debug, **kwargs)

    def apply_combined_differential_threshold(self, gray: np.ndarray, **kwargs) -> np.ndarray:
        return apply_combined_differential_threshold(gray, debug_callback=self.debug, **kwargs)

    def apply_method(self, method: ThresholdMethod, gray: np.ndarray, **kwargs) -> np.ndarray:
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

    def get_available_methods(self) -> list:
        return [method.value for method in ThresholdMethod]

    def get_method_info(self, method: ThresholdMethod) -> Dict[str, Any]:
        method_info = {
            ThresholdMethod.GLOBAL: {
                "description": "Fixed threshold value",
                "parameters": ["threshold", "invert"],
                "use_case": "Simple binary separation with known threshold",
            },
            ThresholdMethod.OTSU: {
                "description": "Automatic threshold selection using Otsu's method",
                "parameters": ["invert"],
                "use_case": "Bimodal intensity distributions",
            },
            ThresholdMethod.ADAPTIVE: {
                "description": "Local threshold based on neighborhood statistics",
                "parameters": ["method", "thresh_type", "block_size", "c_constant", "invert"],
                "use_case": "Varying illumination conditions",
            },
            ThresholdMethod.MULTI_OTSU: {
                "description": "Multi-level Otsu for multiple intensity classes",
                "parameters": ["classes", "invert"],
                "use_case": "Images with multiple intensity regions",
            },
            ThresholdMethod.LINE_ENHANCED: {
                "description": "Enhanced detection of linear structures",
                "parameters": ["kernel_length", "rotation_angle", "invert"],
                "use_case": "Grid lines and linear patterns",
            },
            ThresholdMethod.MORPHOLOGICAL: {
                "description": "Otsu followed by morphological operations",
                "parameters": ["operation", "kernel_size", "invert"],
                "use_case": "Noise reduction and shape refinement",
            },
            ThresholdMethod.COMBINED_DIFFERENTIAL: {
                "description": "Production method: Multi-Otsu with spurious element removal",
                "parameters": [],
                "use_case": "Thick grid detection with cellular content removal",
            },
        }
        return method_info.get(
            method, {"description": "Unknown method", "parameters": [], "use_case": "Unknown"}
        )
