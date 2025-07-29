import os
from config.config_schema import DebugConfig
from utils.detection.grid_detection_drawer import GridDetectionDrawer
import numpy as np


class Debugger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Use 'Debugger.get_instance()' to access the Debugger instance.")

    @classmethod
    def get_instance(cls) -> "Debugger":
        if not cls._instance:
            cls._instance = super(Debugger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, debug_config: DebugConfig) -> None:
        if self._initialized:
            return
        self._visualization_active = debug_config.enabled and debug_config.visualization
        self._output_dir = debug_config.output_dir
        if self._visualization_active and self._output_dir:
            os.makedirs(self._output_dir, exist_ok=True)
        self._initialized = True

    def create_drawer(self, overlay: np.ndarray) -> "GridDetectionDrawer":
        return GridDetectionDrawer(overlay, enabled=self._visualization_active, output_dir=self._output_dir)
