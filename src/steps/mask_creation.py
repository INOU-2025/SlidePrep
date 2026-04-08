from typing import Any

import cv2
import numpy as np

from api.schemas import StepResult
from src.core.step import PipelineStep


class MaskCreationStep(PipelineStep):
    """Pipeline step for generating a binary mask from refined contours."""

    def __init__(self) -> None:
        """Initialize the mask creation step."""
        super().__init__(name="mask_creation", config=None)

    def run(self, data: Any) -> StepResult:
        """Create mask image from refined detection contours.

        Args:
            data: Dictionary containing refined detection results produced by
                :class:`GridRefinementStep`. Must include a ``detections`` key
                mapping orientations to contour information.

        Returns:
            :class:`~api.schemas.StepResult` with the generated mask.

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

        return StepResult.from_array(mask)

