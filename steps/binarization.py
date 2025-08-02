import numpy as np
from typing import Optional

from core.step import PipelineStep
from config.config_schema import BinarizationConfig
from utils.binarization.binarization_methods import BinarizationMethods


class BinarizationStep(PipelineStep):
    def __init__(self, config: BinarizationConfig, **kwargs) -> None:
        super().__init__(name="Binarization", config=config, **kwargs)
        
        # Initialize binarization methods utility with debug callback
        self.methods = BinarizationMethods(debug_callback=self.debug)

    def run(self, data: np.ndarray) -> np.ndarray:
        """
        Apply binarization to a grayscale image.
        
        Args:
            data: Grayscale image as numpy array
            
        Returns:
            Binarized image as numpy array
        """
        # Validate input image
        self._validate_image_input(data)

        # Convert to grayscale if needed
        if len(data.shape) == 3:
            if data.shape[2] == 3:  # RGB
                gray = np.dot(data[...,:3], [0.2989, 0.5870, 0.1140]).astype(np.uint8)
            elif data.shape[2] == 4:  # RGBA
                gray = np.dot(data[...,:3], [0.2989, 0.5870, 0.1140]).astype(np.uint8)
            else:  # Single channel 3D
                gray = data.squeeze()
        else:
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
        
        self.log(f"Binarization completed")
        return binary_image
