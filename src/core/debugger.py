import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import cv2
import numpy as np

from src.config import DebugConfig
from src.core.logger import Logger
from src.utils.debug.drawer import Drawer
from src.utils.debug.result_writer import ResultWriter


class ArtifactSink(ABC):
    """Interface for persisting debug artifacts."""

    @abstractmethod
    def save_image(self, filename: str, image: np.ndarray) -> None:
        """Save an image artifact."""

    @abstractmethod
    def save_data(
        self,
        filename: str,
        results: Any,
        writer: Optional[ResultWriter] = None,
        metadata: Any | None = None,
    ) -> None:
        """Persist structured data."""


class LocalArtifactSink(ArtifactSink):
    """Persist artifacts to the local filesystem."""

    def __init__(self, base_path: str = "") -> None:
        self._base_path = base_path
        if self._base_path:
            os.makedirs(self._base_path, exist_ok=True)

    def _full_path(self, filename: str) -> str:
        return os.path.join(self._base_path, filename) if self._base_path else filename

    def save_image(self, filename: str, image: np.ndarray) -> None:
        cv2.imwrite(self._full_path(filename), image)

    def save_data(
        self,
        filename: str,
        results: Any,
        writer: Optional[ResultWriter] = None,
        metadata: Any | None = None,
    ) -> None:
        path = self._full_path(filename)
        if writer is not None:
            writer.write(path, results, metadata)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(results))


class InMemoryArtifactSink(ArtifactSink):
    """Store artifacts in memory for streaming or deferred handling."""

    def __init__(self) -> None:
        self.images: Dict[str, np.ndarray] = {}
        self.data: Dict[str, Any] = {}

    def save_image(self, filename: str, image: np.ndarray) -> None:
        self.images[filename] = image

    def save_data(
        self,
        filename: str,
        results: Any,
        writer: Optional[ResultWriter] = None,
        metadata: Any | None = None,
    ) -> None:
        self.data[filename] = {"results": results, "metadata": metadata}


class Debugger:
    """Debugger with optional drawer for enhanced visualization and result persistence."""

    def __init__(
        self,
        logger: Logger,
        debug_config: DebugConfig,
        debug_enabled: bool = True,
        drawer: Optional[Drawer] = None,
        writer: Optional[ResultWriter] = None,
        sink: Optional[ArtifactSink] = None,
    ) -> None:
        """Create a debugger instance."""

        self._enabled = debug_enabled
        self._save_images = debug_config.saved_artifact_type in {"image", "both"}
        self._save_composite = debug_config.save_composite_img
        self._path = debug_config.path
        self._save_results = debug_config.saved_artifact_type in {"data", "both"}

        self._logger = logger
        self._drawer = drawer
        self._writer = writer

        if sink is not None:
            self._sink = sink
        else:
            if debug_config.artifact_sink == "memory":
                self._sink = InMemoryArtifactSink()
            else:
                self._sink = LocalArtifactSink(self._path)

    def _save_image(
        self, filename: str, image: np.ndarray, original: Optional[np.ndarray] = None
    ) -> None:
        """Persist an image to the debug output directory.

        Saves either the processed image or a side-by-side composite of the
        original and processed images depending on configuration.
        """
        if not self._enabled or not self._save_images or image is None:
            return

        try:
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
            self._sink.save_image(filename, image_to_save)
        except Exception as e:
            self._logger.warning(f"Failed to save image {filename}: {e}")

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
            self._logger.warning("No result writer attached; results not saved.")
            return

        if not filename:
            self._logger.warning("No filename provided for saving results.")
            return

        try:
            self._sink.save_data(filename, results, self._writer, metadata)
        except Exception as e:
            self._logger.warning(f"Failed to save results {filename}: {e}")
