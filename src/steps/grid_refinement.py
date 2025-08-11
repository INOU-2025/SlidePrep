from typing import Any, Dict, List, Optional, Tuple

import cv2
import joblib
import numpy as np

from src.core.step import PipelineStep
from config.config_schema import GridRefinementConfig
from src.utils.detection.models import DetectionStrategy, Orientation, DetectionRegion
from src.utils.detection.contour_analysis import analyze_contour
from src.core.container import Container


class GridRefinementStep(PipelineStep):
    """Pipeline step for refining grid detection results."""

    def __init__(self, config: GridRefinementConfig, name: str = "grid_refinement", **kwargs: Any) -> None:
        """Initialize grid refinement step with configuration."""
        super().__init__(name=name, config=config, **kwargs)

        if config is None:
            raise ValueError(f"[{name}] GridRefinementConfig is required")

        self.model = joblib.load(config.classifier.model_path)
        self.log(
            f"Loaded refinement model from {config.classifier.model_path}")

    def _filter_out_border_detections(self, analyzed_contours: List[dict], orientation, strategy) -> List[dict]:
        """
        Filter out border detections using the classifier.

        Args:
            analyzed_contours: List of analyzed contour dictionaries.
            orientation: Orientation enum.
            strategy: DetectionStrategy enum.

        Returns:
            List of top contours after refinement, each including its analysis.
        """
        scored_contours: List[tuple[float, dict]] = []
        orientation_name = orientation.value if hasattr(
            orientation, "value") else str(orientation)
        for idx, item in enumerate(analyzed_contours):
            analysis = item["analysis"]
            feature_values = []
            for feature in self.config.classifier.features:
                value = analysis.get(feature)
                if value is None:
                    value = 0.0
                feature_values.append(value)

            probability = self.model.predict_proba([feature_values])[0][1]

            self.debug(
                f"Contour {idx + 1}: probability={probability:.3f}, threshold={self.config.classifier.threshold}")

            if probability > self.config.classifier.threshold:
                scored_contours.append((probability, item))

        # Rank remaining contours by probability and keep only the top one per orientation
        if scored_contours:
            scored_contours.sort(key=lambda x: x[0], reverse=True)
            # Return a dict with both the original item and its analysis
            top_contours = [scored_contours[0][1]]
        else:
            top_contours = []

        self.debug(
            f"Kept {len(top_contours)}/{len(analyzed_contours)} {orientation_name} contours after refinement"
        )

        return top_contours

    def _adjust_contour_to_target_angle(
        self, contour: np.ndarray, analysis: dict, target_angle: float, tolerance: float = 0.0
    ) -> np.ndarray:
        """
        Rotate the contour to match the target angle, using centroid and current angle from analysis.

        Args:
            contour: The contour to adjust (Nx1x2 array).
            analysis: Dictionary containing contour analysis, must include 'angle' and 'centroid'.
            target_angle: The desired angle (in degrees).

        Returns:
            Rotated contour as a numpy array.
        """
        if target_angle is None:
            self.debug("No target angle specified, returning original contour")
            return contour

        current_angle = analysis.get("long_side_angle", 0.0)
        centroid = analysis.get("centroid", (0.0, 0.0))
        angle_diff = target_angle - current_angle

        if abs(angle_diff) < tolerance:
            self.debug(
                f"Angle difference {angle_diff:.2f}° is within tolerance ({tolerance}°); no adjustment needed."
            )
            return contour

        center = (float(centroid[0]), float(centroid[1]))
        rot_mat = cv2.getRotationMatrix2D(center, -angle_diff, 1.0)
        rotated = cv2.transform(contour, rot_mat)

        self.debug(
            f"Adjusted contour from angle {current_angle:.2f}° to target {target_angle:.2f}° (Δ={angle_diff:.2f}°), centroid={center}"
        )
        return rotated

    def _expand_min_box_to_image(
        self,
        min_rect: Tuple[Tuple[float, float], Tuple[float, float], float],
        computed_orientation: Orientation,
        image_shape: Tuple[int, int]
    ) -> np.ndarray:
        """
        Expand the min area rectangle along its computed orientation so it traverses the image.

        Args:
            min_rect: ((cx, cy), (w, h), angle) as from cv2.minAreaRect
            computed_orientation: Orientation enum (Orientation.HORIZONTAL or Orientation.VERTICAL)
            image_shape: (height, width) of the image

        Returns:
            np.ndarray: 4x2 array of box points for the expanded rectangle
        """
        (cx, cy), (w, h), angle = min_rect
        H, W = image_shape[:2]

        if computed_orientation == Orientation.HORIZONTAL:
            new_w = W * 1.5  # Span the image width
            new_h = h
        else:  # Orientation.VERTICAL
            new_w = w
            new_h = H * 1.5  # Span the image height

        expanded_rect = ((cx, cy), (new_w, new_h), angle)
        box = cv2.boxPoints(expanded_rect)
        return box.astype(np.float32)

    def run(self, data: Any) -> tuple[Dict[str, Any], Optional[dict]]:
        """Refine detection results by analyzing non-general contours.

        Args:
            data: results dict from grid detection step.

        Returns:
            Tuple containing refined results and original metadata.
        """
        if not isinstance(data, dict):
            raise TypeError("GridRefinementStep expects results dictionary")

        detections = data.get("detections", {})
        strategies = data.get("strategies", {})
        image_shape = Container.resolve("pipeline_context").image_shape
        angle_tolerance = self.config.target_inclination_angles.get(
            "tolerance", None)

        refined: Dict[Orientation, Any] = {}

        for orientation, contour_dicts in detections.items():
            strategy = strategies.get(orientation)
            orientation_name = orientation.value if hasattr(
                orientation, "value") else str(orientation)
            target_angle = self.config.target_inclination_angles.get(
                orientation_name, None)

            if strategy == DetectionStrategy.GENERAL:
                self.debug(
                    f"Keeping {len(contour_dicts)} {orientation_name} contours from general detection"
                )

                contours = [c.get("contour") for c in contour_dicts if c.get(
                    "contour") is not None]
                zone = contour_dicts[0].get(
                    "zone", DetectionRegion.CENTER) if contour_dicts else DetectionRegion.CENTER

                if contours:
                    if len(contours) > 1:
                        self.debug(
                            f"Merging {len(contours)} contours for {orientation_name} orientation"
                        )
                        contour = cv2.convexHull(
                            np.vstack(contours))
                    else:
                        contour = contours[0]

                    analysis = analyze_contour(
                        contour,
                        orientation=orientation,
                        strategy=strategy
                    )
                    contour = self._adjust_contour_to_target_angle(
                        contour, analysis, target_angle, angle_tolerance
                    )
                    analysis = analyze_contour(
                        contour,
                        orientation=orientation,
                        strategy=strategy
                    )
                    # Expand the box after orientation adjustment
                    expanded_box = self._expand_min_box_to_image(
                        analysis["min_area_rect"], analysis["computed_orientation"], image_shape)
                    # Use expanded_box as the new contour
                    analysis["expanded_box"] = expanded_box
                    refined[orientation] = [
                        {"contour": expanded_box, "zone": zone, "analysis": analysis}]
                else:
                    refined[orientation] = []
                continue

            # Analyze contours generated by any other strategy and use the classifier to filter the ones that are not an actual detection
            self.debug(
                f"Analyzing {len(contour_dicts)} {orientation_name} contours from {getattr(strategy, 'value', strategy)} detection")

            analyzed_contours = []
            for item in contour_dicts:
                contour = item.get("contour")
                if contour is not None:
                    analysis = analyze_contour(
                        contour,
                        orientation=orientation,
                        strategy=strategy,
                        image_shape=image_shape
                    )
                    contour = self._adjust_contour_to_target_angle(
                        contour, analysis, target_angle, angle_tolerance
                    )
                    analysis = analyze_contour(
                        contour,
                        orientation=orientation,
                        strategy=strategy,
                        image_shape=image_shape
                    )
                    # Expand the box after orientation adjustment
                    expanded_box = self._expand_min_box_to_image(
                        analysis["min_area_rect"],
                        analysis["computed_orientation"],
                        image_shape
                    )
                    analysis["expanded_box"] = expanded_box
                    enriched_item = {
                        **item, "contour": expanded_box, "analysis": analysis}
                    analyzed_contours.append(enriched_item)

            top_contours = self._filter_out_border_detections(
                analyzed_contours, orientation, strategy)

            refined[orientation] = top_contours

        refined_results = {"detections": refined, "strategies": strategies}
        return refined_results, None
