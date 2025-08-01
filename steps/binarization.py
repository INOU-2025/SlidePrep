import cv2
import numpy as np
from typing import Optional

from core.step import PipelineStep
from core.context import PipelineContext
from config.config_schema import BinarizationConfig
from core.logger import Logger
from core.debugger import Debugger
from utils.binarization_methods import BinarizationMethods


class BinarizationStep(PipelineStep):
    def __init__(self, config: BinarizationConfig, logger: Optional[Logger] = None, debugger: Optional[Debugger] = None, **kwargs):
        super().__init__(name="Binarization", logger=logger, debugger=debugger, **kwargs)
        self.config = config
        
        # Initialize binarization methods utility with debug callback
        self.methods = BinarizationMethods(debug_callback=self.debug)

    def run(self, ctx: PipelineContext) -> None:
        if ctx.gray_image is None:
            raise ValueError("gray_image is required for binarization")

        gray = ctx.gray_image
        fname = ctx.image_name or "unnamed"
        
        self.log(f"Starting binarization for {fname} using combined differential method")
        
        # Apply combined differential threshold (production method)
        binary_image = self.methods.apply_combined_differential_threshold(gray)
        
        # Store the result in context
        ctx.binarized_image = binary_image
        
        # Debug visualization if enabled
        if self.debugger and self.debugger.is_enabled():
            self._debug_visualize(gray, binary_image, fname)
        
        self.log(f"Binarization completed for {fname}")

    def _debug_visualize(self, gray: np.ndarray, binary: np.ndarray, fname: str) -> None:
        """Create debug visualization using the specialized binarization drawer."""
        try:
            # Create specialized binarization drawer
            drawer = self.debugger.create_drawer("binarization", gray)
            
            # Set the binarized result with method information
            method_info = "combined_differential"
            drawer.set_binarized_image(binary, method_info)
            
            # Save debug image
            debug_filename = f"{fname}_binarization_debug.png"
            drawer.save(debug_filename)
            self.debug(f"Saved debug visualization: {debug_filename}")
            
        except Exception as e:
            self.debug(f"Failed to create debug visualization: {e}")
