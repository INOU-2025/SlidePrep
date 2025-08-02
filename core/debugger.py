import os
from typing import Dict, Type, Optional
import numpy as np
import cv2

from config.config_schema import DebugConfig
from utils.debug.base_drawer import BaseDrawer
from utils.debug.grid_detection_drawer import GridDetectionDrawer
from utils.debug.binarization_drawer import BinarizationDrawer


class Debugger:
    """Registry-based debugger with dynamic drawer creation."""
    _registry: Dict[str, Type[BaseDrawer]] = {}

    def __init__(self, debug_config: DebugConfig, debug_enabled: bool = True):
        self._enabled = debug_enabled
        self._save_composite = debug_config.save_composite
        self._output_dir = debug_config.output_dir
        if self._enabled and self._output_dir:
            os.makedirs(self._output_dir, exist_ok=True)

    def is_enabled(self) -> bool:
        """Check if debugging is enabled."""
        return self._enabled
    

    def save_image(self, filename: str, image: np.ndarray, original: Optional[np.ndarray] = None) -> None:
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

    @classmethod
    def register_drawer(cls, key: str, drawer_cls: Type[BaseDrawer]) -> None:
        """Register a drawer class for a specific step type."""
        cls._registry[key] = drawer_cls

    @classmethod
    def get_registered_drawers(cls) -> Dict[str, Type[BaseDrawer]]:
        """Get all registered drawer types."""
        return cls._registry.copy()

    def create_drawer(self, key: str, image: np.ndarray, **kwargs) -> BaseDrawer:
        """Create a drawer instance for the specified step type."""
        if key not in self._registry:
            raise KeyError(f"Drawer '{key}' not registered. Available: {list(self._registry.keys())}")
        
        drawer_cls = self._registry[key]
        return drawer_cls(image, enabled=self._enabled, output_dir=self._output_dir, **kwargs)


# Register default drawers
Debugger.register_drawer("grid_detection", GridDetectionDrawer)
Debugger.register_drawer("binarization", BinarizationDrawer)
