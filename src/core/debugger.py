import os
from typing import Optional, Any
import numpy as np
import cv2

from config.config_schema import DebugConfig
from src.utils.debug.drawer import Drawer
from src.utils.debug.result_writer import ResultWriter
from src.core.logger import Logger


class Debugger:
    """Debugger with optional drawer for enhanced visualization and result persistence."""

    def __init__(
        self,
        logger: Logger,
        debug_config: DebugConfig,
        debug_enabled: bool = True,
        drawer: Optional[Drawer] = None,
        writer: Optional[ResultWriter] = None,
    ) -> None:
        """Create a debugger instance.

        Args:
            logger: Application logger for reporting issues.
            debug_config: Configuration controlling debug output behavior.
            debug_enabled: Whether debugging features are active.
            drawer: Optional drawer used to annotate images before saving.
            writer: Optional result writer used to persist structured data.
        """
        self._enabled = debug_enabled
        self._save_composite = debug_config.save_composite
        self._path = debug_config.path
        self._save_results = debug_config.save_results
        self._logger = logger
        self._drawer = drawer
        self._writer = writer
        if self._enabled and self._path:
            os.makedirs(self._path, exist_ok=True)

    def _save_image(
        self, filename: str, image: np.ndarray, original: Optional[np.ndarray] = None
    ) -> None:
        """Persist an image to the debug output directory.

        Saves either the processed image or a side-by-side composite of the
        original and processed images depending on configuration.
        """
        if not self._enabled or image is None:
            return

        try:
            output_path = (
                os.path.join(self._path, filename)
                if self._path
                else filename
            )

            if original is not None and self._save_composite:
                base = original
                result = image
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
        except Exception as e:
            self._logger.warning(f"Failed to save image to {output_path}: {e}")

    def save_debug_image(
        self,
        filename: str,
        image: np.ndarray,
        results: Any | None = None,
        metadata: Any | None = None,
    ) -> None:
        """Generate and save a debug visualization.

        Uses the attached drawer to overlay results on the original image when
        available. If no drawer is provided, the processed image is saved
        directly.
        """
        if not self._enabled:
            return

        try:
            if self._drawer is not None:
                enhanced_image = self._drawer.draw(image, results, metadata)
                if enhanced_image is not None:
                    self._save_image(filename, enhanced_image)
            else:
                # When no drawer, save the results (processed image) instead of original
                image_to_save = results if results is not None else image
                self._save_image(filename, image_to_save)
        except Exception as e:
            self._logger.warning(f"Failed to save debug image {filename}: {e}")

    def save_results(self, filename: str, results: Any, metadata: Any = None) -> None:
        """Serialize detection results using the configured writer.

        Args:
            filename: Name of the file where results will be stored.
            results: Structured data produced by the pipeline step.
            metadata: Optional extra information to persist alongside results.
        """
        if not self._enabled or not self._save_results:
            return

        if self._writer is None:
            self._logger.warning(
                "No result writer attached; results not saved.")
            return

        if not filename:
            self._logger.warning("No filename provided for saving results.")
            return

        try:
            output_path = (
                os.path.join(self._path, filename)
                if self._path
                else filename
            )
            self._writer.write(output_path, results, metadata)
        except Exception as e:
            self._logger.warning(
                f"Failed to save results to {output_path}: {e}")
