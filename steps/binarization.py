import cv2
import numpy as np
from typing import Optional

from core.step import PipelineStep
from config.config_schema import BinarizationConfig
from utils.binarization.binarization_methods import BinarizationMethods


class BinarizationStep(PipelineStep):
    def __init__(self, config: BinarizationConfig, **kwargs) -> None:
        super().__init__(name="Binarization", **kwargs)
        self.config = config
        
        # Initialize binarization methods utility with debug callback
        self.methods = BinarizationMethods(debug_callback=self.debug)

    def run(self, data: np.ndarray) -> np.ndarray:
        """
        Apply binarization to a grayscale image.
        
        Args:
            data: Grayscale image as numpy array
            
        Returns:
            Binarized image as numpy array
            
        Raises:
            ValueError: If input data is None or invalid
            TypeError: If input data is not a numpy array
        """
        if data is None:
            raise ValueError("Input image is required for binarization")
        
        if not isinstance(data, np.ndarray):
            raise TypeError("Input data must be a numpy array")
        
        if data.size == 0:
            raise ValueError("Input image cannot be empty")

        gray = data
        self.log(f"Starting binarization using {self.config.threshold_method} method")
        
        # Apply the configured binarization method
        try:
            if self.config.threshold_method == "combined_differential":
                binary_image = self.methods.apply_combined_differential_threshold(gray)
            else:
                raise ValueError(f"Unknown threshold method: {self.config.threshold_method}")
        except Exception as e:
            self.log(f"Binarization failed: {e}")
            raise
        
        # Debug visualization if enabled
        if self.debugger and self.debugger.is_enabled():
            self._debug_visualize(gray, binary_image)
        
        self.log(f"Binarization completed")
        return binary_image

    def _debug_visualize(self, gray: np.ndarray, binary: np.ndarray) -> None:
        """Create debug visualization using the specialized binarization drawer."""
        if not isinstance(gray, np.ndarray) or not isinstance(binary, np.ndarray):
            self.debug("Invalid input arrays for debug visualization")
            return
            
        try:
            # Create specialized binarization drawer
            drawer = self.debugger.create_drawer("binarization", gray)
            
            # Set the binarized result with method information
            method_info = self.config.threshold_method
            drawer.set_binarized_image(binary, method_info)
            
            # Save debug image
            debug_filename = f"binarization_{method_info}_debug.png"
            drawer.save(debug_filename)
            self.debug(f"Saved debug visualization: {debug_filename}")
            
        except Exception as e:
            self.debug(f"Failed to create debug visualization: {e}")
