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

from src.core.bootstrap import (
    bootstrap,
    get_config,
    get_logger,
    get_debugger,
    get_pipeline_context,
)
from src.core.step import PipelineStep
from src.utils.debug.drawer import Drawer
from src.utils.debug.result_writer import ResultWriter
from src.utils.image_utils import get_supported_image_formats
from src.utils.detection.detection_result_dict import DetectionResultDict


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
        Process all items in the configured input directory.
        When ``test.input_type`` is ``"data"``, the runner loads serialized
        results (``*.json``) alongside each image and passes them to
        ``step.run``.

        Returns
        -------
        If any non-image results are produced, returns a list of aggregated results.
        Otherwise, returns None.
        """
        input_dir = self._cfg.general_config.input_path
        if not input_dir or not os.path.exists(input_dir):
            self._logger.error(
                f"Input directory not found or not specified: {input_dir}"
            )
            return

        supported_formats = get_supported_image_formats()
        image_files = []
        for fname in sorted(os.listdir(input_dir)):
            if fname.lower().endswith(supported_formats):
                if self._cfg.general_config.suffix_filter:
                    name_without_ext = os.path.splitext(fname)[0]
                    if not name_without_ext.endswith(
                        self._cfg.general_config.suffix_filter
                    ):
                        continue
                image_files.append(fname)

        if not image_files:
            self._logger.warning(f"No supported images found in {input_dir}")
            return

        self._logger.info(
            f"Starting batch processing of {len(image_files)} images from {input_dir}"
        )

        processed = 0
        output_suffix = (
            self._cfg.general_config.output_suffix
            or step.name.lower().replace(" ", "_")
        )

        debug_cfg = self._cfg.debug_config
        if debug_cfg.save_aggregated_data and debug_cfg.saved_artifact_type in {
            "data",
            "both",
        }:
            result_filename = debug_cfg.result_file_name
        else:
            result_filename = None

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

                read_data = (
                    self._cfg.test_config
                    and self._cfg.test_config.input_type == "data"
                )
                if read_data:
                    result_path = os.path.splitext(image_path)[0] + ".json"
                    dict_with_enum = DetectionResultDict.from_json(result_path)
                    intermediate_data = dict_with_enum.to_plain_dict()
                    if intermediate_data is None:
                        self._logger.warning(
                            f"No intermediate results found for {fname}"
                        )
                    result, metadata = step.run(intermediate_data)
                else:
                    result, metadata = step.run(image)

                base_debug_filename = f"{base_name}{output_suffix}"
                image_debug_filename = f"{base_debug_filename}.png"
                self._debugger.save_debug_image(
                    image_debug_filename, image, result, metadata
                )

                if not isinstance(result, (np.ndarray,)):
                    if result_filename:
                        aggregated_results.append({"filename": fname, "result": result})
                    else:
                        self._debugger.save_results(base_debug_filename, result)

                self._logger.debug(f"Successfully processed {fname}")
                processed += 1

            except Exception as e:
                self._logger.error(f"Error processing {fname}: {e}")

        self._logger.info(
            f"Batch processing completed: {processed}/{len(image_files)} images processed successfully"
        )

        if result_filename and len(aggregated_results) > 0:
            metadata = {"image_shape": get_pipeline_context().image_shape}
            self._debugger.save_results(result_filename, aggregated_results, metadata)
