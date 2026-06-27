from typing import Any, Dict, List, Optional, Tuple

import cv2
import joblib
import numpy as np

from src.core.step_result import StepResult
from src.config import GridRefinementConfig
from src.core.step import PipelineStep
from src.utils.detection.contour_analysis import analyze_contour
from src.utils.detection.models import DetectionStrategy, Orientation, DetectionRegion



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
    raise ValueError(
        f"Invalid contour shape {a.shape}; expected (N,2) or (N,1,2)")


def _edge_unit_vector(
    computed_orientation: Orientation,
    image_shape: Tuple[int, int],
    center: Tuple[float, float],
    zone: DetectionRegion | None,
) -> np.ndarray:
    """
    Unit vector pointing toward the image edge we consider 'outside' for thickness bias.
    Uses zone when provided; otherwise chooses nearest edge along the normal axis.
    """
    H, W = image_shape[:2]
    cx, cy = center

    if computed_orientation == Orientation.HORIZONTAL:
        # normal axis is vertical (top/bottom)
        if zone == DetectionRegion.TOP:
            return np.array([0.0, -1.0], dtype=np.float32)
        if zone == DetectionRegion.BOTTOM:
            return np.array([0.0, 1.0], dtype=np.float32)
        # fallback by proximity
        return np.array([0.0, -1.0], dtype=np.float32) if cy < H * 0.5 else np.array([0.0, 1.0], dtype=np.float32)

    else:  # VERTICAL
        # normal axis is horizontal (left/right)
        if zone == DetectionRegion.LEFT:
            return np.array([-1.0, 0.0], dtype=np.float32)
        if zone == DetectionRegion.RIGHT:
            return np.array([1.0, 0.0], dtype=np.float32)
        # fallback by proximity
        return np.array([-1.0, 0.0], dtype=np.float32) if cx < W * 0.5 else np.array([1.0, 0.0], dtype=np.float32)


def _long_edge_and_normal(min_rect: Tuple[Tuple[float, float], Tuple[float, float], float]) -> tuple[np.ndarray, np.ndarray]:
    """
    From a minAreaRect, compute a unit tangent vector (along the long edge) and its unit normal.
    Normal is chosen with arbitrary sign; caller can flip sign according to desired direction.
    """
    box = cv2.boxPoints(min_rect).astype(np.float32)  # (4,2)
    # Edges: (0->1), (1->2), (2->3), (3->0)
    edges = [box[(i + 1) % 4] - box[i] for i in range(4)]
    lengths = [float(np.linalg.norm(e)) for e in edges]
    i_long = int(np.argmax(lengths))
    t = edges[i_long]
    norm_t = np.linalg.norm(t)
    if norm_t == 0:
        # degenerate; default to x-axis
        t = np.array([1.0, 0.0], dtype=np.float32)
    else:
        t = t / norm_t
    n = np.array([-t[1], t[0]], dtype=np.float32)  # perpendicular
    return t, n


# ----------------- main step -----------------

class GridRefinementStep(PipelineStep):
    """Pipeline step for refining grid detection results."""

    EXPANSION_FACTOR: float = 1.5

    def __init__(self, config: GridRefinementConfig) -> None:
        """Load the pre-trained border classifier from config.classifier.model_path."""
        super().__init__(name="grid_refinement", config=config)

        self.model = joblib.load(config.classifier.model_path)
        self.log(
            f"Loaded refinement model from {config.classifier.model_path}")

    def _filter_out_border_detections(self, analyzed_contours: List[dict], orientation, strategy) -> List[dict]:
        """
        Filter out border detections using the classifier.
        Keeps at most one contour (highest probability above threshold).
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

            probability = float(
                self.model.predict_proba([feature_values])[0][1])
            self.debug(
                f"Contour {idx + 1}: probability={probability:.3f}, "
                f"threshold={self.config.classifier.threshold}"
            )

            if probability > self.config.classifier.threshold:
                scored_contours.append((probability, item))

        if scored_contours:
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
        Rotate contour around its centroid to match target angle if outside tolerance.
        """
        current_angle = float(analysis.get("long_side_angle", 0.0))
        centroid = analysis.get("centroid", (0.0, 0.0))
        angle_diff = target_angle - current_angle

        if abs(angle_diff) < (tolerance or 0.0):
            self.debug(
                f"Angle difference {angle_diff:.2f}° within tolerance ({tolerance}°); no adjustment.")
            return _as_cnt(contour)

        center = (float(centroid[0]), float(centroid[1]))
        rot_mat = cv2.getRotationMatrix2D(center, -angle_diff, 1.0)
        rotated = cv2.transform(_as_cnt(contour), rot_mat)
        self.debug(
            f"Adjusted contour {current_angle:.2f}° -> {target_angle:.2f}° (Δ={angle_diff:.2f}°), centroid={center}")
        return rotated

    def _expand_min_rect(
        self,
        min_rect: Tuple[Tuple[float, float], Tuple[float, float], float],
        computed_orientation: Orientation,
        image_shape: Tuple[int, int]
    ) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
        """
        Rect -> Rect: expand the rectangle along its long axis to traverse the image.
        """
        (cx, cy), (w, h), angle = min_rect
        H, W = image_shape[:2]

        if computed_orientation == Orientation.HORIZONTAL:
            new_w, new_h = W * self.EXPANSION_FACTOR, h
        else:
            new_w, new_h = w, H * self.EXPANSION_FACTOR

        return ((cx, cy), (new_w, new_h), angle)

    def _set_short_side_even(
        self,
        min_rect: Tuple[Tuple[float, float], Tuple[float, float], float],
        computed_orientation: Orientation,
        target_thickness: float,
    ) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
        """
        Rect -> Rect (GENERAL): set the short side to target_thickness, keep center fixed.
        """
        (cx, cy), (w, h), angle = min_rect
        if computed_orientation == Orientation.HORIZONTAL:
            return ((cx, cy), (w, float(target_thickness)), angle)
        else:
            return ((cx, cy), (float(target_thickness), h), angle)

    def _set_short_side_uneven(
        self,
        min_rect: Tuple[Tuple[float, float], Tuple[float, float], float],
        computed_orientation: Orientation,
        target_thickness: float,
        image_shape: Tuple[int, int],
        zone: DetectionRegion | None,
        bias: Optional[float] = None,
    ) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
        """
        Rect -> Rect (NON-GENERAL): set short side to target_thickness,
        shifting the center along the rectangle's normal so most of the added thickness
        goes toward the 'edge' (based on zone/position) and a smaller amount the other way.

        bias in (0.5, 1.0]: fraction of the ADDED thickness allocated toward the edge.
        """
        if bias is None:
            bias = 0.5

        (cx, cy), (w, h), angle = min_rect
        long_len, short_len = (
            w, h) if computed_orientation == Orientation.HORIZONTAL else (h, w)

        # New thickness and total added thickness
        T = float(target_thickness)
        d_total = T - float(short_len)  # can be negative (shrink)

        # Find normal to long edge
        # unit normal (arbitrary sign)
        _, n = _long_edge_and_normal(min_rect)
        # Decide which side is 'edge'
        e = _edge_unit_vector(computed_orientation,
                              image_shape, (cx, cy), zone)
        if np.dot(n, e) < 0:
            n = -n  # flip normal to point toward selected edge

        # Center shift: Δc = (Δpref - Δopp)/2 = (bias - 0.5) * (T - s)
        delta_c = (bias - 0.5) * d_total
        c_shift = n * float(delta_c)

        c_new = (float(cx) + float(c_shift[0]), float(cy) + float(c_shift[1]))
        size_new = (long_len, T) if computed_orientation == Orientation.HORIZONTAL else (
            T, long_len)
        return (c_new, size_new, angle)

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
            self.debug(
                "No target angle specified. Returning the original contour.")
            return {"contour": cnt0, "zone": zone, "analysis": analysis0}

        # rotate using centroid + long_side_angle from analysis0
        cnt_rot = self._adjust_contour_to_target_angle(
            cnt0, analysis0, target_angle, angle_tolerance)

        # minRect on the rotated contour (no extra analysis yet)
        min_rect_rot = cv2.minAreaRect(cnt_rot)
        (w, h) = min_rect_rot[1]
        computed_ori = Orientation.HORIZONTAL if w >= h else Orientation.VERTICAL

        # expand (rect->rect) then convert to box points
        expanded_rect = self._expand_min_rect(
            min_rect_rot, computed_ori, image_shape)
        expanded_box = cv2.boxPoints(expanded_rect).astype(np.float32)

        # final analysis only once (post-expand)
        analysis_expanded = analyze_contour(
            _as_cnt(expanded_box), orientation, strategy, image_shape)
        analysis_expanded["expanded_rect"] = expanded_rect

        return {"contour": expanded_box, "zone": zone, "analysis": analysis_expanded}

    def run(self, data: Any) -> StepResult:
        """Refine detection results by analyzing and adjusting contours."""
        if not isinstance(data, dict):
            raise TypeError("GridRefinementStep expects results dictionary")

        detections = data.get("detections", {})
        strategies = data.get("strategies", {})
        if not self.container:
            raise ValueError("Container not available for GridRefinementStep")
        image_shape = self.container.resolve("pipeline_context").image_shape
        angle_tolerance = self.config.target_inclination_angles.get(
            "tolerance", None)
        target_thickness = float(self.config.target_thickness)
        thickness_bias = float(self.config.thickness_bias)

        refined: Dict[Orientation, Any] = {}

        for orientation, contour_dicts in detections.items():
            strategy = strategies.get(orientation)
            orientation_name = orientation.value if hasattr(
                orientation, "value") else str(orientation)
            target_angle = self.config.target_inclination_angles.get(
                orientation_name, None)

            if strategy == DetectionStrategy.GENERAL:
                self.debug(
                    f"Keeping {len(contour_dicts)} {orientation_name} contours from general detection")

                contours = [c.get("contour") for c in contour_dicts if c.get(
                    "contour") is not None]
                zone = contour_dicts[0].get(
                    "zone", DetectionRegion.CENTER) if contour_dicts else DetectionRegion.CENTER

                if contours:
                    # normalize and merge if needed
                    if len(contours) > 1:
                        self.debug(
                            f"Merging {len(contours)} contours for {orientation_name} orientation")
                        stacked = np.vstack(
                            [_as_cnt(c).reshape(-1, 2) for c in contours]).astype(np.float32)
                        cnt = cv2.convexHull(_as_cnt(stacked))
                    else:
                        cnt = _as_cnt(contours[0])

                    processed = self._process_contour(
                        cnt, orientation, strategy, target_angle, angle_tolerance, image_shape, zone
                    )

                    # EVEN thickness (centered) for GENERAL
                    analysis = processed["analysis"]
                    # expanded rect
                    min_rect = analysis["min_area_rect"]
                    computed_orientation = analysis["computed_orientation"]

                    even_rect = self._set_short_side_even(
                        min_rect, computed_orientation, target_thickness)
                    even_box = cv2.boxPoints(even_rect).astype(np.float32)

                    analysis["thickness_adjusted_box"] = even_box
                    processed["contour"] = even_box

                    refined[orientation] = [processed]
                else:
                    refined[orientation] = []
                continue

            # -------- non-GENERAL path --------
            self.debug(
                f"Analyzing {len(contour_dicts)} {orientation_name} contours "
                f"from {getattr(strategy, 'value', strategy)} detection"
            )

            analyzed_contours = []
            for item in contour_dicts:
                contour = item.get("contour")
                if contour is not None:
                    zone = item.get("zone")
                    analysis = analyze_contour(
                        _as_cnt(contour), orientation, strategy, image_shape)
                    analyzed_contours.append(
                        {**item, "contour": contour, "zone": zone, "analysis": analysis})

            # Filter first
            top_contours = self._filter_out_border_detections(
                analyzed_contours, orientation, strategy)

            # Now process the filtered contours
            post_processed = []
            for item in top_contours:
                zone = item.get("zone")
                processed = self._process_contour(
                    item["contour"], orientation, strategy, target_angle, angle_tolerance, image_shape, zone
                )

                # UNEVEN thickness for non-GENERAL: bias growth toward the image edge
                analysis = processed["analysis"]
                # expanded rect
                min_rect = analysis["min_area_rect"]
                computed_orientation = analysis["computed_orientation"]

                uneven_rect = self._set_short_side_uneven(
                    min_rect,
                    computed_orientation,
                    target_thickness,
                    image_shape,
                    zone,
                    bias=thickness_bias
                )
                uneven_box = cv2.boxPoints(uneven_rect).astype(np.float32)

                analysis["thickness_adjusted_box"] = uneven_box
                processed["contour"] = uneven_box

                post_processed.append({**item, **processed})

            refined[orientation] = post_processed

        refined_results = {"detections": refined, "strategies": strategies}
        return StepResult.from_data(refined_results)

