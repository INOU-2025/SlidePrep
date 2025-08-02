import os
from typing import Optional
import numpy as np
import cv2

from config.config_schema import DebugConfig
from utils.debug.base_drawer import BaseDrawer


class Debugger:
    """
    Debugger with optional drawer for enhanced visualization.
    
    """

    def __init__(self, debug_config: DebugConfig, debug_enabled: bool = True, drawer: Optional[BaseDrawer] = None):
        self._enabled = debug_enabled
        self._save_composite = debug_config.save_composite
        self._output_dir = debug_config.output_dir
        self._drawer = drawer  # Single optional drawer instance
        if self._enabled and self._output_dir:
            os.makedirs(self._output_dir, exist_ok=True)

    def _save_image(self, filename: str, image: np.ndarray, original: Optional[np.ndarray] = None) -> None:
        """Save an image to the debug output directory."""
        if not self._enabled or image is None:
            return

        try:
            output_path = (
                os.path.join(self._output_dir, filename)
                if self._output_dir
                else filename
            )

            # Optionally compose with original for comparison
            if original is not None and self._save_composite:
                base = original
                result = image
                # Ensure both images are in BGR format with same dimensions
                if len(base.shape) == 2:
                    base = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
                if len(result.shape) == 2:
                    result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
                if base.shape != result.shape:
                    result = cv2.resize(result, (base.shape[1], base.shape[0]))
                image_to_save = np.hstack((base, result))
            else:
                image_to_save = image

            cv2.imwrite(output_path, image_to_save)
        except Exception:
            # Debug saving should never interfere with main processing
            pass

    def save_debug_image(self, filename: str, image: np.ndarray, results=None, metadata=None) -> None:
        """Save a debug image, using drawer if available."""
        if not self._enabled:
            return
            
        try:
            if self._drawer is not None:
                # Use drawer to create enhanced visualization
                enhanced_image = self._drawer.draw(image, results, metadata)
                if enhanced_image is not None:
                    self._save_image(filename, enhanced_image)
            else:
                # No drawer, save the plain image
                self._save_image(filename, image)
        except Exception:
            # Debug operations should never interfere with main processing
            pass
