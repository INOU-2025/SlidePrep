import cv2
import numpy as np

from core.step import PipelineStep
from config.config_schema import BinarizationConfig
from utils.binarization.binarization_methods import BinarizationMethods


class BinarizationStep(PipelineStep):
    def __init__(self, config: BinarizationConfig, **kwargs):
        super().__init__(name="Binarization", **kwargs)
        self.config = config
        
        # Initialize binarization methods utility with debug callback
        self.methods = BinarizationMethods(debug_callback=self.debug)

    def run(self, data: np.ndarray) -> np.ndarray:
        """
        Apply binarization to a grayscale image.
        
        Args:
            data: Input grayscale image as numpy array
            
        Returns:
            Binarized image as numpy array
        """
        self.log(f"Starting binarization with method: {self.config.threshold_method}")
        
        gray = data  # Input is already grayscale
        
        # Apply binarization
        binary_image = self.methods.apply_binarization(
            gray, 
            self.config.threshold_method, 
            self.config.threshold_value
        )
        
        # Debug visualization if enabled
        if self.debugger and self.debugger.is_enabled():
            self._debug_visualize(gray, binary_image)
        
        self.log(f"Binarization completed")
        return binary_image

    def _debug_visualize(self, gray: np.ndarray, binary: np.ndarray) -> None:
        """Create debug visualization using the specialized binarization drawer."""
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

    @property
    def logger(self):
        """Get the logger from the container."""
        from core.container import Container
        return Container.resolve("logger")

    @property
    def debugger(self):
        """Get the debugger from the container."""
        from core.container import Container
        try:
            return Container.resolve("debugger")
        except KeyError:
            return None
