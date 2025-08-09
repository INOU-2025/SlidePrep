import numpy as np
from typing import Any

from core.step import PipelineStep
from config.config_schema import BinarizationConfig
from utils.binarization import BinarizationMethods


class BinarizationStep(PipelineStep):
    """Pipeline step for converting grayscale images to binary using thresholding methods.
    
    Applies configurable binarization algorithms to separate foreground from background,
    with automatic grayscale conversion for color inputs.
    """
    
    def __init__(self, config: BinarizationConfig, **kwargs: Any) -> None:
        """Initialize binarization step with configuration.
        
        Args:
            config: Binarization configuration specifying threshold method and parameters.
            **kwargs: Additional arguments passed to parent class.
        """
        super().__init__(name="binarization", config=config, **kwargs)
        self.methods = BinarizationMethods(debug_callback=self.debug)

    def run(self, data: np.ndarray) -> np.ndarray:
        """Convert grayscale image to binary using configured thresholding method.
        
        Automatically converts color images to grayscale before applying binarization.
        Uses production-optimized algorithms for consistent results across image types.
        
        Args:
            data: Input image as numpy array. Can be grayscale (2D) or color (3D).
            
        Returns:
            Binary image as uint8 numpy array with values 0 (background) and 255 (foreground).
            
        Raises:
            ValueError: If threshold method is unknown or image validation fails.
            TypeError: If input is not a numpy array.
        """
        self._validate_image_input(data)

        if len(data.shape) == 3:
            if data.shape[2] == 3:
                gray = np.dot(data[...,:3], [0.2989, 0.5870, 0.1140]).astype(np.uint8)
            elif data.shape[2] == 4:
                gray = np.dot(data[...,:3], [0.2989, 0.5870, 0.1140]).astype(np.uint8)
            else:
                gray = data.squeeze()
        else:
            gray = data

        self.debug(
            f"Starting binarization using {self.config.threshold_method} method")

        try:
            if self.config.threshold_method == "combined_differential":
                binary_image = self.methods.apply_combined_differential_threshold(
                    gray)
            else:
                raise ValueError(
                    f"Unknown threshold method: {self.config.threshold_method}")
        except Exception as e:
            self.error(f"Binarization failed: {e}")
            raise

        self.debug(f"Binarization completed successfully")
        return binary_image, None
