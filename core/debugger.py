import os
from typing import Dict, Type, Optional
import numpy as np
import cv2

from config.config_schema import DebugConfig
from utils.debug.base_drawer import BaseDrawer
from utils.debug.grid_detection_drawer import GridDetectionDrawer


class Debugger:
    """
    Registry-based debugger with automatic drawer integration.
    
    """
    _registry: Dict[str, Type[BaseDrawer]] = {}

    def __init__(self, debug_config: DebugConfig, debug_enabled: bool = True):
        self._enabled = debug_enabled
        self._save_composite = debug_config.save_composite
        self._output_dir = debug_config.output_dir
        self._drawer_instances: Dict[str, BaseDrawer] = {}  # Cache drawer instances
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

    @classmethod
    def register_drawer(cls, key: str, drawer_cls: Type[BaseDrawer]) -> None:
        """Register a drawer class for a specific step type."""
        cls._registry[key] = drawer_cls

    @classmethod
    def get_registered_drawers(cls) -> Dict[str, Type[BaseDrawer]]:
        """Get all registered drawer types."""
        return cls._registry.copy()

    def create_drawer(self, key: str, **kwargs) -> BaseDrawer:
        """Create a drawer instance for the specified step type."""
        if key not in self._registry:
            raise KeyError(f"Drawer '{key}' not registered. Available: {list(self._registry.keys())}")
        
        drawer_cls = self._registry[key]
        return drawer_cls(**kwargs)

    def _get_drawer(self, step_key: str) -> Optional[BaseDrawer]:
        """Get or create a cached drawer instance for the specified step."""
        if step_key not in self._registry:
            return None
            
        # Reuse cached instance if available
        if step_key not in self._drawer_instances:
            self._drawer_instances[step_key] = self.create_drawer(step_key)
            
        return self._drawer_instances[step_key]

    def save_debug_image(self, step_key: str, filename: str, image: np.ndarray, results=None, metadata=None) -> None:
        """Save a debug image, using registered drawer if available."""
        if not self._enabled:
            return
            
        try:
            # Check if there's a registered drawer for this step
            drawer = self._get_drawer(step_key)
            if drawer is not None:
                # Use drawer to create enhanced visualization
                enhanced_image = drawer.draw(image, results, metadata)
                if enhanced_image is not None:
                    self._save_image(filename, enhanced_image)
            else:
                # No drawer registered, save the plain image
                self._save_image(filename, image)
        except Exception:
            # Debug operations should never interfere with main processing
            pass


# Register default drawers
Debugger.register_drawer("grid_detection", GridDetectionDrawer)
