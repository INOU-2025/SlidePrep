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
        output_suffix: str = "result",
    ) -> None:
        """Process all images in the configured input directory.

        Parameters
        ----------
        step:
            Instantiated pipeline step to execute.
        output_suffix:
            Suffix to add to output filenames (e.g. "binarized", "grid_detected").
        """
        
        # Get input directory from config
        input_dir = self.cfg.general_config.input_path
        if not input_dir:
            print("Error: input_path must be specified in the general config section")
            return
        
        if not os.path.exists(input_dir):
            print(f"Error: Input directory not found: {input_dir}")
            return

        # Get output directory
        output_dir = self.cfg.general_config.output_path or "output"
        os.makedirs(output_dir, exist_ok=True)

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
            print(f"No supported images found in {input_dir}")
            return

        print(f"Processing {len(image_files)} images from {input_dir}")
        print(f"Output will be saved to: {output_dir}")

        # Process each image (services injected via container)
        processed = 0
        for fname in image_files:
            try:
                # Load image
                image_path = os.path.join(input_dir, fname)
                image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if image is None:
                    print(f"⚠️  Could not load {fname}")
                    continue

                base_name = os.path.splitext(fname)[0]
                self.logger.info(f"Processing {fname}")

                # Run the step - simple input/output
                result = step.run(image)

                # Handle different return types
                if isinstance(result, tuple):
                    # For steps that return (image, metadata) like grid detection
                    result_image, metadata = result
                    print(f"✓ Processed {fname} (metadata: {metadata})")
                else:
                    # For steps that return just an image like binarization
                    result_image = result
                    print(f"✓ Processed {fname}")

                # Save result
                config_suffix = self.cfg.general_config.output_suffix or ""
                output_filename = f"{base_name}{config_suffix}_{output_suffix}.png"
                output_path = os.path.join(output_dir, output_filename)
                cv2.imwrite(output_path, result_image)
                
                # Also save via debugger for debug output (if debug enabled)
                if self.cfg.debug_active and result_image is not None:
                    debug_filename = f"{base_name}_{output_suffix}.png"
                    self.debugger.save_image(debug_filename, result_image, image)
                
                processed += 1

            except Exception as e:
                print(f"✗ Error processing {fname}: {e}")

        print(f"\nCompleted: {processed}/{len(image_files)} images processed successfully")