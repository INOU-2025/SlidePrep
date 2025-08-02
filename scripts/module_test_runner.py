from __future__ import annotations

"""
Simple test runner for pipeline steps.

This class sets up the common components (configuration, logger, debugger)
and offers a run method that processes images from a directory using a given PipelineStep.
It automatically loads images, processes them, and saves the results.

This keeps individual test scripts compact and ensures a consistent workflow.
"""

import os
import cv2
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from core.bootstrap import bootstrap, get_config, get_logger, get_debugger
from core.step import PipelineStep
from core.debugger import Debugger
from utils.debug.base_drawer import BaseDrawer
from utils.image_utils import get_supported_image_formats


@dataclass
class StepTestRunner:
    """Simple test runner for processing images with pipeline steps."""

    _config_path: str
    _drawer: Optional[BaseDrawer] = None

    def __post_init__(self) -> None:
        # Bootstrap the application with basic services and optional drawer
        bootstrap(self._config_path, self._drawer)
        
        # Get services from container
        self._cfg = get_config()
        self._logger = get_logger()
        self._debugger = get_debugger()  # Debugger already has the drawer attached

    @property
    def cfg(self):
        """Get configuration (read-only access)."""
        return self._cfg

    @property
    def logger(self):
        """Get logger (read-only access)."""
        return self._logger

    @property
    def debugger(self):
        """Get debugger (read-only access)."""
        return self._debugger

    def run_on_directory(
        self,
        step: PipelineStep,
        output_suffix: str,
    ) -> None:
        """Process all images in the configured input directory.

        Parameters
        ----------
        step:
            Instantiated pipeline step to execute.
        output_suffix:
            Suffix to add to output filenames (e.g. "binarized", "grid_detected").
        """
        
        # Validate required parameters
        if not output_suffix:
            self._logger.warning("output_suffix parameter is required but not provided")
            return
        
        # Get input directory from config
        input_dir = self._cfg.general_config.input_path
        if not input_dir or not os.path.exists(input_dir):
            self._logger.error(f"Input directory not found or not specified: {input_dir}")
            return

        # Find all supported images
        supported_formats = get_supported_image_formats()
        image_files = []
        for fname in sorted(os.listdir(input_dir)):
            if fname.lower().endswith(supported_formats):
                # Apply suffix filter if specified
                if self._cfg.general_config.suffix_filter:
                    name_without_ext = os.path.splitext(fname)[0]
                    if not name_without_ext.endswith(self._cfg.general_config.suffix_filter):
                        continue
                image_files.append(fname)

        if not image_files:
            self._logger.warning(f"No supported images found in {input_dir}")
            return

        self._logger.info(f"Processing {len(image_files)} images from {input_dir}")

        # Process each image
        processed = 0
        step_key = step.name.lower().replace(" ", "_") if hasattr(step, 'name') else output_suffix
        
        for fname in image_files:
            try:
                # Load image
                image_path = os.path.join(input_dir, fname)
                image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if image is None:
                    self.logger.warning(f"Could not load {fname}")
                    continue

                base_name = os.path.splitext(fname)[0]
                self._logger.info(f"Processing {fname}")

                # Run the step
                result = step.run(image)

                # Save debug output - debugger handles everything automatically
                debug_filename = f"{base_name}_{output_suffix}.png"
                self._debugger.save_debug_image(debug_filename, image, result)
                    
                self._logger.info(f"Processed {fname}")
                processed += 1

            except Exception as e:
                self._logger.error(f"Error processing {fname}: {e}")

        self._logger.info(f"Completed: {processed}/{len(image_files)} images processed successfully")