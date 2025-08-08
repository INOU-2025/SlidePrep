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
from typing import Optional, List, Dict
import numpy as np

from core.bootstrap import bootstrap, get_config, get_logger, get_debugger, get_pipeline_context
from core.step import PipelineStep
from utils.debug.drawer import Drawer
from utils.debug.result_writer import ResultWriter
from utils.image_utils import get_supported_image_formats


@dataclass
class StepTestRunner:
    """Simple test runner for processing images with pipeline steps."""

    _config_path: str
    _drawer: Optional[Drawer] = None
    _writer: Optional[ResultWriter] = None

    def __post_init__(self) -> None:
        bootstrap(self._config_path, self._drawer, self._writer)

        self._cfg = get_config()
        self._logger = get_logger()
        self._debugger = get_debugger()

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
    ) -> None:
        """
        Process all images in the configured input directory.

        Returns
        -------
        If any non-image results are produced, returns a list of aggregated results.
        Otherwise, returns None.
        """
        input_dir = self._cfg.general_config.input_path
        if not input_dir or not os.path.exists(input_dir):
            self._logger.error(
                f"Input directory not found or not specified: {input_dir}")
            return

        supported_formats = get_supported_image_formats()
        image_files = []
        for fname in sorted(os.listdir(input_dir)):
            if fname.lower().endswith(supported_formats):
                if self._cfg.general_config.suffix_filter:
                    name_without_ext = os.path.splitext(fname)[0]
                    if not name_without_ext.endswith(self._cfg.general_config.suffix_filter):
                        continue
                image_files.append(fname)

        if not image_files:
            self._logger.warning(f"No supported images found in {input_dir}")
            return

        self._logger.info(
            f"Starting batch processing of {len(image_files)} images from {input_dir}")

        processed = 0
        output_suffix = self._cfg.general_config.output_suffix or step.name.lower().replace(" ", "_")
        aggregated_results: List[Dict] = []

        for fname in image_files:
            try:
                image_path = os.path.join(input_dir, fname)
                image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if image is None:
                    self._logger.warning(f"Could not load {fname}")
                    continue

                base_name = os.path.splitext(fname)[0]
                self._logger.debug(f"Processing {fname}")

                result, metadata = step.run(image)

                debug_filename = f"{base_name}{output_suffix}.png"
                self._debugger.save_debug_image(debug_filename, image, result, metadata)
                
                if not isinstance(result, (np.ndarray,)):
                    aggregated_results.append({
                        "filename": fname,
                        "result": result
                    })

                self._logger.debug(f"Successfully processed {fname}")
                processed += 1

            except Exception as e:
                self._logger.error(f"Error processing {fname}: {e}")

        self._logger.info(
            f"Batch processing completed: {processed}/{len(image_files)} images processed successfully")

        if self._writer and len(aggregated_results) > 0:
            metadata = {"image_shape": get_pipeline_context().image_shape}
            self._writer.write("prueba.csv", aggregated_results, metadata)
