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

        Behaviour depends on ``test.input_type``:

        - ``"image"`` (default): files from ``test.input_path`` are passed
          directly to ``step.run``. For each file, the runner looks for a
          source image with the same filename in ``general.input_path`` and
          stores its path in the pipeline context. This allows steps to load the
          original image independently (useful when the provided file is a
          mask).
        - ``"data"``: JSON files from ``test.input_path`` are loaded and
          provided to ``step.run``. Corresponding source images are located in
          ``general.input_path`` and the pipeline context is updated with their
          paths before processing.

        Returns
        -------
        None
            Aggregated results are written to disk when configured.
        """
        gen_cfg = self._cfg.general_config
        test_cfg = self._cfg.test_config

        input_dir = (
            test_cfg.input_path if test_cfg and test_cfg.input_path else gen_cfg.input_path
        )
        if not input_dir or not os.path.exists(input_dir):
            self._logger.error(
                f"Input directory not found or not specified: {input_dir}"
            )
            return

        supported_formats = get_supported_image_formats()
        if test_cfg and test_cfg.input_type == "data":
            files = []
            for fname in sorted(os.listdir(input_dir)):
                if fname.lower().endswith(".json"):
                    files.append(fname)
        else:
            files = []
            for fname in sorted(os.listdir(input_dir)):
                if fname.lower().endswith(supported_formats):
                    files.append(fname)

        total_files = len(files)
        if test_cfg and test_cfg.max_images is not None:
            files = files[:test_cfg.max_images]
            if len(files) < total_files:
                self._logger.info(
                    f"Limiting processing to {len(files)} items "
                    f"(max_images={test_cfg.max_images})"
                )

        if not files:
            self._logger.warning(f"No supported inputs found in {input_dir}")
            return

        self._logger.info(
            f"Starting batch processing of {len(files)} items from {input_dir}"
        )

        processed = 0

        debug_cfg = self._cfg.debug_config
        if debug_cfg.save_aggregated_data and debug_cfg.saved_artifact_type in {
            "data",
            "both",
        }:
            result_filename = debug_cfg.result_file_name
        else:
            result_filename = None

        aggregated_results: List[Dict] = []

        for fname in files:
            try:
                read_data = test_cfg and test_cfg.input_type == "data"
                base_name = os.path.splitext(fname)[0]

                data_path = os.path.join(input_dir, fname)

                context_image_path = None
                candidate = os.path.join(gen_cfg.input_path, fname)
                if os.path.exists(candidate):
                    context_image_path = candidate
                else:
                    for ext in supported_formats:
                        candidate = os.path.join(gen_cfg.input_path, base_name + ext)
                        if os.path.exists(candidate):
                            context_image_path = candidate
                            break

                if context_image_path is None:
                    self._logger.warning(
                        f"No source image found for {fname} in {gen_cfg.input_path}"
                    )
                    continue

                ctx = get_pipeline_context()
                ctx.input_image_path = context_image_path

                source_image = cv2.imread(context_image_path, cv2.IMREAD_GRAYSCALE)
                if source_image is None:
                    self._logger.warning(
                        f"Could not load {context_image_path}"
                    )
                    continue
                ctx.image_shape = (source_image.shape[1], source_image.shape[0])

                self._logger.debug(f"Processing {fname}")

                if read_data:
                    dict_with_enum = DetectionResultDict.from_json(data_path)
                    intermediate_data = dict_with_enum.to_plain_dict()
                    if intermediate_data is None:
                        self._logger.warning(
                            f"No intermediate results found for {fname}"
                        )
                    result, metadata = step.run(intermediate_data)
                else:
                    if data_path == context_image_path:
                        data_image = source_image
                    else:
                        data_image = cv2.imread(data_path, cv2.IMREAD_GRAYSCALE)
                        if data_image is None:
                            self._logger.warning(f"Could not load {data_path}")
                            continue
                    result, metadata = step.run(data_image)

                image_debug_filename = f"{base_name}.png"
                self._debugger.save_debug_image(
                    image_debug_filename, source_image, result, metadata
                )

                if not isinstance(result, (np.ndarray,)):
                    if result_filename:
                        aggregated_results.append({"filename": fname, "result": result})
                    else:
                        self._debugger.save_results(base_name, result)

                self._logger.debug(f"Successfully processed {fname}")
                processed += 1

            except Exception as e:
                self._logger.error(f"Error processing {fname}: {e}")

        self._logger.info(
            f"Batch processing completed: {processed}/{len(files)} items processed successfully"
        )

        if result_filename and len(aggregated_results) > 0:
            metadata = {"image_shape": get_pipeline_context().image_shape}
            self._debugger.save_results(result_filename, aggregated_results, metadata)
