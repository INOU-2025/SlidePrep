import os
from typing import Dict, Type, Optional
import numpy as np
import cv2

from config.config_schema import DebugConfig
from utils.debug.base_drawer import BaseDrawer
from utils.debug.grid_detection_drawer import GridDetectionDrawer
from utils.debug.binarization_drawer import BinarizationDrawer


class Debugger:
    """
    Registry-based debugger with dynamic drawer creation.
    Supports extensible drawer registration for different pipeline steps.
    """
    _instance = None
    _registry: Dict[str, Type[BaseDrawer]] = {}

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Use 'Debugger.get_instance()' to access the Debugger instance.")

    @classmethod
    def get_instance(cls) -> "Debugger":
        if not cls._instance:
            cls._instance = super(Debugger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, debug_config: DebugConfig, debug_enabled: bool = True) -> None:
        if self._initialized:
            return
        self._visualization_active = debug_enabled
        self._output_dir = debug_config.output_dir
        if self._visualization_active and self._output_dir:
            os.makedirs(self._output_dir, exist_ok=True)
        self._initialized = True

    def is_enabled(self) -> bool:
        """Check if debugging is enabled."""
        return self._visualization_active

    @classmethod
    def register_drawer(cls, key: str, drawer_cls: Type[BaseDrawer]) -> None:
        """
        Register a drawer class for a specific step type.
        
        Args:
            key: Step identifier (e.g., 'grid_detection', 'binarization')
            drawer_cls: Drawer class that inherits from BaseDrawer
        """
        cls._registry[key] = drawer_cls

    @classmethod
    def get_registered_drawers(cls) -> Dict[str, Type[BaseDrawer]]:
        """Get all registered drawer types."""
        return cls._registry.copy()

    def create_drawer(self, key: str, image: np.ndarray, **kwargs) -> BaseDrawer:
        """
        Create a drawer instance for the specified step type.
        
        Args:
            key: Step identifier (e.g., 'grid_detection', 'binarization')
            image: Image to use as the base for visualization
            **kwargs: Additional arguments to pass to the drawer constructor
            
        Returns:
            Drawer instance for the specified step type
            
        Raises:
            KeyError: If the drawer type is not registered
        """
        if key not in self._registry:
            raise KeyError(f"Drawer '{key}' not registered. Available: {list(self._registry.keys())}")
        
        drawer_cls = self._registry[key]
        return drawer_cls(image, enabled=self._visualization_active, output_dir=self._output_dir, **kwargs)


# Register default drawers
Debugger.register_drawer("grid_detection", GridDetectionDrawer)
Debugger.register_drawer("binarization", BinarizationDrawer)
