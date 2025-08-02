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
from utils.image_utils import get_supported_image_formats


@dataclass
class StepTestRunner:
    """Simple test runner for processing images with pipeline steps."""

    config_path: str

    def __post_init__(self) -> None:
        # Bootstrap the application with all services
        bootstrap(self.config_path)
        
        # Get services from container
        self.cfg = get_config()
        self.logger = get_logger()
        self.debugger = get_debugger()

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
            self.logger.warning("output_suffix parameter is required but not provided")
            return
        
        # Get input directory from config
        input_dir = self.cfg.general_config.input_path
        if not input_dir or not os.path.exists(input_dir):
            self.logger.error(f"Input directory not found or not specified: {input_dir}")
            return

        # Find all supported images
        supported_formats = get_supported_image_formats()
        image_files = []
        for fname in sorted(os.listdir(input_dir)):
            if fname.lower().endswith(supported_formats):
                # Apply suffix filter if specified
                if self.cfg.general_config.suffix_filter:
                    name_without_ext = os.path.splitext(fname)[0]
                    if not name_without_ext.endswith(self.cfg.general_config.suffix_filter):
                        continue
                image_files.append(fname)

        if not image_files:
            self.logger.warning(f"No supported images found in {input_dir}")
            return

        self.logger.info(f"Processing {len(image_files)} images from {input_dir}")

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
                self.logger.info(f"Processing {fname}")

                # Run the step
                result = step.run(image)

                # Save debug output - debugger handles everything automatically
                debug_filename = f"{base_name}_{output_suffix}.png"
                self.debugger.save_debug_image(step_key, debug_filename, image, result)
                    
                self.logger.info(f"Processed {fname}")
                processed += 1

            except Exception as e:
                self.logger.error(f"Error processing {fname}: {e}")

        self.logger.info(f"Completed: {processed}/{len(image_files)} images processed successfully")