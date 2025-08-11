from typing import Any, Dict, List, Optional, Tuple

import cv2
import joblib
import numpy as np

from src.core.step import PipelineStep
from config.config_schema import GridRefinementConfig
from src.utils.detection.models import DetectionStrategy, Orientation, DetectionRegion
from src.utils.detection.contour_analysis import analyze_contour
from src.core.container import Container


def _as_cnt(a: np.ndarray) -> np.ndarray:
    """
    Ensure OpenCV-friendly contour: shape (N,1,2), dtype float32.
    Accepts (N,2) or (N,1,2).
    """
    a = np.asarray(a, dtype=np.float32)
    if a.ndim == 2 and a.shape[1] == 2:
        return a.reshape((-1, 1, 2))
    if a.ndim == 3 and a.shape[1] == 1 and a.shape[2] == 2:
        return a
    raise ValueError(f"Invalid contour shape {a.shape}; expected (N,2) or (N,1,2)")


class GridRefinementStep(PipelineStep):
    """Pipeline step for refining grid detection results."""

    EXPANSION_FACTOR: float = 1.5  # consider moving to GridRefinementConfig

    def __init__(self, config: GridRefinementConfig, name: str = "grid_refinement", **kwargs: Any) -> None:
        super().__init__(name=name, config=config, **kwargs)

        if config is None:
            raise ValueError(f"[{name}] GridRefinementConfig is required")

        self.model = joblib.load(config.classifier.model_path)
        self.log(f"Loaded refinement model from {config.classifier.model_path}")

    def _filter_out_border_detections(self, analyzed_contours: List[dict], orientation, strategy) -> List[dict]:
        """
        Filter out border detections using the classifier.

        Args:
            analyzed_contours: List of analyzed contour dictionaries.
            orientation: Orientation enum.
            strategy: DetectionStrategy enum.

        Returns:
            List with at most one top contour after refinement.
        """
        scored_contours: List[tuple[float, dict]] = []
        orientation_name = orientation.value if hasattr(orientation, "value") else str(orientation)

        for idx, item in enumerate(analyzed_contours):
            analysis = item["analysis"]
            feature_values = []
            for feature in self.config.classifier.features:
                value = analysis.get(feature)
                if value is None:
                    value = 0.0
                feature_values.append(value)

            probability = float(self.model.predict_proba([feature_values])[0][1])
            self.debug(
                f"Contour {idx + 1}: probability={probability:.3f}, "
                f"threshold={self.config.classifier.threshold}"
            )

            if probability > self.config.classifier.threshold:
                scored_contours.append((probability, item))

        if scored_contours:
            # pick the best without sorting the whole list
            best_item = max(scored_contours, key=lambda x: x[0])[1]
            top_contours = [best_item]
        else:
            top_contours = []

        self.debug(
            f"Kept {len(top_contours)}/{len(analyzed_contours)} {orientation_name} contours after refinement"
        )
        return top_contours

    def _adjust_contour_to_target_angle(
        self, contour: np.ndarray, analysis: dict, target_angle: float, tolerance: Optional[float] = 0.0
    ) -> np.ndarray:
        """
        Rotate the contour to match the target angle, using centroid and current angle from analysis.
        """
        current_angle = float(analysis.get("long_side_angle", 0.0))
        centroid = analysis.get("centroid", (0.0, 0.0))
        angle_diff = target_angle - current_angle

        if abs(angle_diff) < (tolerance or 0.0):
            self.debug(
                f"Angle difference {angle_diff:.2f}° is within tolerance ({tolerance}°); no adjustment needed."
            )
            return _as_cnt(contour)

        center = (float(centroid[0]), float(centroid[1]))
        rot_mat = cv2.getRotationMatrix2D(center, -angle_diff, 1.0)
        rotated = cv2.transform(_as_cnt(contour), rot_mat)

        self.debug(
            f"Adjusted contour from angle {current_angle:.2f}° to target {target_angle:.2f}° "
            f"(Δ={angle_diff:.2f}°), centroid={center}"
        )
        return rotated

    def _expand_min_rect(
        self,
        min_rect: Tuple[Tuple[float, float], Tuple[float, float], float],
        computed_orientation: Orientation,
        image_shape: Tuple[int, int]
    ) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
        """
        Rect -> Rect: expand the min area rectangle along its computed orientation so it traverses the image.
        """
        (cx, cy), (w, h), angle = min_rect
        H, W = image_shape[:2]

        if computed_orientation == Orientation.HORIZONTAL:
            new_w, new_h = W * self.EXPANSION_FACTOR, h
        else:
            new_w, new_h = w, H * self.EXPANSION_FACTOR

        return ((cx, cy), (new_w, new_h), angle)

    def _set_short_side(
        self,
        min_rect: Tuple[Tuple[float, float], Tuple[float, float], float],
        computed_orientation: Orientation,
        target_thickness: float,
    ) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
        """
        Rect -> Rect: adjust the short side to target_thickness; keep the long side as-is.
        """
        (cx, cy), (w, h), angle = min_rect
        if computed_orientation == Orientation.HORIZONTAL:
            new_w, new_h = w, float(target_thickness)
        else:
            new_w, new_h = float(target_thickness), h
        return ((cx, cy), (new_w, new_h), angle)

    def _process_contour(
        self,
        contour: np.ndarray,
        orientation: Orientation,
        strategy: DetectionStrategy,
        target_angle: Optional[float],
        angle_tolerance: Optional[float],
        image_shape: Tuple[int, int],
        zone: DetectionRegion
    ) -> dict:
        """
        Analyze once, rotate if needed, expand via rect->rect, and analyze final expanded box once.
        Returns expanded contour and its analysis (post-expand).
        """
        cnt0 = _as_cnt(contour)
        analysis0 = analyze_contour(cnt0, orientation, strategy, image_shape)

        if target_angle is None:
            self.debug("No target angle specified. Returning the original contour.")
            return {"contour": cnt0, "zone": zone, "analysis": analysis0}

        # rotate using centroid + long_side_angle from analysis0
        cnt_rot = self._adjust_contour_to_target_angle(cnt0, analysis0, target_angle, angle_tolerance)

        # minRect on the rotated contour (no extra analysis yet)
        min_rect_rot = cv2.minAreaRect(cnt_rot)
        (w, h) = min_rect_rot[1]
        computed_ori = Orientation.HORIZONTAL if w >= h else Orientation.VERTICAL

        # expand (rect->rect) then convert to box points
        expanded_rect = self._expand_min_rect(min_rect_rot, computed_ori, image_shape)
        expanded_box = cv2.boxPoints(expanded_rect).astype(np.float32)

        # final analysis only once (post-expand)
        analysis_expanded = analyze_contour(_as_cnt(expanded_box), orientation, strategy, image_shape)
        analysis_expanded["expanded_rect"] = expanded_rect

        return {"contour": expanded_box, "zone": zone, "analysis": analysis_expanded}

    def run(self, data: Any) -> tuple[Dict[str, Any], Optional[dict]]:
        """Refine detection results by analyzing non-general contours."""
        if not isinstance(data, dict):
            raise TypeError("GridRefinementStep expects results dictionary")

        detections = data.get("detections", {})
        strategies = data.get("strategies", {})
        image_shape = Container.resolve("pipeline_context").image_shape
        angle_tolerance = self.config.target_inclination_angles.get("tolerance", None)
        target_thickness = float(self.config.target_thickness)

        refined: Dict[Orientation, Any] = {}

        for orientation, contour_dicts in detections.items():
            strategy = strategies.get(orientation)
            orientation_name = orientation.value if hasattr(orientation, "value") else str(orientation)
            target_angle = self.config.target_inclination_angles.get(orientation_name, None)

            if strategy == DetectionStrategy.GENERAL:
                self.debug(f"Keeping {len(contour_dicts)} {orientation_name} contours from general detection")

                contours = [c.get("contour") for c in contour_dicts if c.get("contour") is not None]
                zone = contour_dicts[0].get("zone", DetectionRegion.CENTER) if contour_dicts else DetectionRegion.CENTER

                if contours:
                    # normalize and merge if needed
                    if len(contours) > 1:
                        self.debug(f"Merging {len(contours)} contours for {orientation_name} orientation")
                        stacked = np.vstack([_as_cnt(c).reshape(-1, 2) for c in contours]).astype(np.float32)
                        cnt = cv2.convexHull(_as_cnt(stacked))
                    else:
                        cnt = _as_cnt(contours[0])

                    processed = self._process_contour(
                        cnt, orientation, strategy, target_angle, angle_tolerance, image_shape, zone
                    )

                    # set thickness using rect->rect based on expanded analysis
                    analysis = processed["analysis"]
                    min_rect = analysis["min_area_rect"]            # expanded rect
                    computed_orientation = analysis["computed_orientation"]

                    thick_rect = self._set_short_side(min_rect, computed_orientation, target_thickness)
                    thickness_adjusted_box = cv2.boxPoints(thick_rect).astype(np.float32)

                    # optional: store thickness-adjusted geometry
                    analysis["thickness_adjusted_box"] = thickness_adjusted_box
                    processed["contour"] = thickness_adjusted_box

                    refined[orientation] = [processed]
                else:
                    refined[orientation] = []
                continue

            self.debug(
                f"Analyzing {len(contour_dicts)} {orientation_name} contours "
                f"from {getattr(strategy, 'value', strategy)} detection"
            )

            analyzed_contours = []
            for item in contour_dicts:
                contour = item.get("contour")
                if contour is not None:
                    zone = item.get("zone", DetectionRegion.CENTER)
                    analysis = analyze_contour(_as_cnt(contour), orientation, strategy, image_shape)
                    analyzed_contours.append({**item, "contour": contour, "zone": zone, "analysis": analysis})

            # Filter first
            top_contours = self._filter_out_border_detections(analyzed_contours, orientation, strategy)

            # Now process the filtered contours
            post_processed = []
            for item in top_contours:
                processed = self._process_contour(
                    item["contour"], orientation, strategy, target_angle, angle_tolerance, image_shape,
                    item.get("zone", DetectionRegion.CENTER)
                )
                post_processed.append({**item, **processed})

            refined[orientation] = post_processed

        refined_results = {"detections": refined, "strategies": strategies}
        return refined_results, None
