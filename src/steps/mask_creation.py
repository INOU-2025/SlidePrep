from typing import Any, Optional

import cv2
import numpy as np

from src.core.step import PipelineStep


class MaskCreationStep(PipelineStep):
    """Pipeline step for generating a binary mask from refined contours."""

    def __init__(self, name: str = "mask_creation", **kwargs: Any) -> None:
        """Initialize the mask creation step."""
        super().__init__(name=name, config=None, **kwargs)

    def run(self, data: Any) -> tuple[np.ndarray, Optional[dict]]:
        """Create mask image from refined detection contours.

        Args:
            data: Dictionary containing refined detection results produced by
                :class:`GridRefinementStep`. Must include a ``detections`` key
                mapping orientations to contour information.

        Returns:
            Tuple of binary mask and optional metadata (always ``None``).

        Raises:
            TypeError: If input is not the expected dictionary structure.
            ValueError: If pipeline context does not provide image shape.
        """
        if not isinstance(data, dict):
            raise TypeError("MaskCreationStep expects results dictionary")

        detections = data.get("detections", {})
        if not self.container:
            raise ValueError("Container not available for MaskCreationStep")
        context = self.container.resolve("pipeline_context")
        image_shape = context.image_shape
        if image_shape is None:
            raise ValueError("Pipeline context lacks image shape information")

        mask = np.zeros((image_shape[1], image_shape[0]), dtype=np.uint8)

        for contour_list in detections.values():
            for item in contour_list:
                contour = item.get("contour")
                if contour is None:
                    continue
                cv2.fillPoly(mask, [np.asarray(contour, dtype=np.int32)], 255)

        return mask, None
