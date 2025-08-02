import cv2
import numpy as np
from typing import Dict, Tuple, Any

from core.step import PipelineStep
from config.config_schema import GridDetectionConfig
from utils.detection import (
    LineTemplateFactory,
    DetectionStatus,
    Detection,
    GridDetectionResult,
    compute_min_required_ratio,
    border_touch_ratio
)


class GridDetectionStep(PipelineStep):
    """
    Pipeline step for detecting grid patterns in binarized images.
    
    This step uses template matching with horizontal and vertical line templates
    to identify grid structures. It performs sophisticated analysis including
    contour validation, angle verification, and dark pixel ratio assessment
    to distinguish genuine grid lines from noise or artifacts.
    
    The detection process includes:
    - Template matching for line patterns
    - Contour area and geometric validation  
    - Dark pixel ratio analysis for line quality
    - Border touching analysis for edge cases
    - Multi-criteria decision making for final classification
    """

    def __init__(self, config: GridDetectionConfig, **kwargs: Any) -> None:
        """
        Initialize grid detection step with configuration.

        Creates horizontal and vertical line templates based on the specified
        dimensions and angle tolerance for detecting grid patterns.

        Args:
            config: Grid detection configuration specifying line dimensions,
                   thresholds, and detection parameters
            **kwargs: Additional arguments passed to parent PipelineStep
        """
        super().__init__(name="GridDetection", config=config, **kwargs)
        factory = LineTemplateFactory(
            length=config.line_length, thickness=config.line_thickness, angle_deg=config.angle_deg)
        self.templates = {
            "horizontal": factory.create("horizontal"),
            "vertical": factory.create("vertical")
        }

    def run(self, data: np.ndarray) -> GridDetectionResult:
        """
        Apply grid detection to a binarized image.

        Performs comprehensive grid pattern detection using template matching
        and sophisticated validation criteria. The process includes image
        preprocessing, template matching for both orientations, contour analysis,
        and multi-criteria classification of detected patterns.

        Args:
            data: Binarized image as numpy array with shape (height, width)
                 Expected to contain binary values (0 or 255)

        Returns:
            GridDetectionResult containing detected grid patterns and summary
            statistics including counts of accepted, rejected, and maybe detections

        Raises:
            ValueError: If input image is invalid or malformed
            TypeError: If input data is not a numpy array
        """
        self._validate_image_input(data)

        working_image = data
        self.debug(
            f"Starting grid detection on {working_image.shape[1]}x{working_image.shape[0]} binary image")

        detections = []

        mean_val = np.mean(working_image)
        if mean_val < 127:
            inverted = cv2.bitwise_not(working_image)
            self.debug(
                f"Inverted binary image for template matching (mean={mean_val:.1f})")
        else:
            inverted = working_image
            self.debug(
                f"Using binary image as-is for template matching (mean={mean_val:.1f})")

        thresholds = {
            "horizontal": self.config.horizontal_area_threshold,
            "vertical": self.config.vertical_area_threshold,
            "length": self.config.length_threshold_factor * max(working_image.shape)
        }
        self.debug(
            f"Length threshold: {thresholds['length']:.1f} (factor: {self.config.length_threshold_factor})")

        stats = {"accept": 0, "reject": 0, "maybe": 0}
        for key, tmpl in self.templates.items():
            t_h, t_w = tmpl.shape
            pad = (t_h // 2, t_w // 2)
            padded = cv2.copyMakeBorder(
                inverted, *pad, *pad[::-1], cv2.BORDER_CONSTANT, value=0)
            result = cv2.matchTemplate(padded, tmpl, cv2.TM_SQDIFF_NORMED)
            mask = (result < np.percentile(
                result, self.config.percentile_thresh)).astype(np.uint8) * 255
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                if cv2.contourArea(cnt) >= thresholds[key]:
                    corrected_contour = cnt + \
                        np.array([t_w // 2, t_h // 2]) - [pad[1], pad[0]]

                    status, rotated_box = self._analyze_contour(
                        corrected_contour, working_image, key, thresholds
                    )

                    detection = Detection(
                        contour=corrected_contour,
                        rotated_box=rotated_box,
                        status=status,
                        orientation=key
                    )
                    detections.append(detection)

                    if status == DetectionStatus.ACCEPT:
                        stats["accept"] += 1
                    elif status == DetectionStatus.REJECT:
                        stats["reject"] += 1
                    elif status == DetectionStatus.MAYBE:
                        stats["maybe"] += 1

        self.log(
            f"Grid detection completed: {stats['accept']} accepted, {stats['reject']} rejected, {stats['maybe']} uncertain")

        return GridDetectionResult(detections=detections, stats=stats)

    def _analyze_contour(self, contour: np.ndarray, gray_image: np.ndarray,
                         line_orientation: str, detection_thresholds: Dict[str, float]) -> Tuple[DetectionStatus, np.ndarray]:
        """
        Analyze a contour using comprehensive detection logic for grid pattern validation.

        Performs sophisticated analysis to determine if a detected contour represents
        a genuine grid line. The analysis includes geometric validation, dark pixel
        ratio assessment, angle verification, and border touching analysis for
        edge cases requiring relaxed criteria.

        The decision process uses multiple validation stages:
        1. High confidence acceptance (dark ratio >= 0.93)
        2. Low confidence rejection (dark ratio < 0.73)  
        3. Edge case analysis with additional criteria for borderline cases

        Args:
            contour: Detected contour points (already position-corrected for template padding)
            gray_image: Grayscale image used for pixel value analysis
            line_orientation: Grid line orientation ('horizontal' or 'vertical')
            detection_thresholds: Dictionary containing area and length thresholds

        Returns:
            Tuple containing:
            - DetectionStatus: ACCEPT, REJECT, or MAYBE classification
            - np.ndarray: Rotated bounding box points for the contour
        """
        area = cv2.contourArea(contour)
        if area == 0:
            return DetectionStatus.REJECT, np.array([])

        rotated_rect = cv2.minAreaRect(contour)
        rotated_box = cv2.boxPoints(rotated_rect).astype(np.intp)

        mask = np.zeros_like(gray_image, dtype=np.uint8)
        cv2.fillPoly(mask, [rotated_box], 1)
        dark_ratio = np.count_nonzero((gray_image == 0) & (
            mask == 1)) / max(np.count_nonzero(mask), 1)

        contour_mask = np.zeros_like(gray_image, dtype=np.uint8)
        cv2.drawContours(contour_mask, [contour], -1, 1, -1)
        contour_dark_ratio = np.count_nonzero((gray_image == 0) & (
            contour_mask == 1)) / max(np.count_nonzero(contour_mask), 1)

        # Calculate angle and length
        min_ratio = compute_min_required_ratio(area)
        (_, _), (w, h), raw_angle = rotated_rect
        angle = raw_angle + 90 if w < h else raw_angle
        angle = ((angle + 180) % 180) - 90
        length = max(w, h)
        angle_valid = (-4 <= angle <= 4) or (86 <= abs(angle) <= 94)

        accepted, maybe, decision = False, False, "REJECT"
        touches, ratio = -1, -1.0

        if dark_ratio >= 0.93:
            accepted, decision = True, "ACCEPT (high confidence)"
        elif dark_ratio < 0.73:
            decision = "REJECT (low confidence)"
        else:
            maybe = True
            decision = "MAYBE (edge case)"
            if length >= detection_thresholds['length']:
                accepted, maybe, decision = True, False, "ACCEPT (length override)"
            elif not angle_valid:
                maybe, decision = False, "REJECT (angle out of bounds)"

        if maybe:
            maybe = False
            touches, ratio = border_touch_ratio(
                rotated_box, line_orientation, gray_image.shape, self.config.margin)
            if contour_dark_ratio > 0.96 and dark_ratio >= 0.83:
                accepted, decision = True, "ACCEPT (contour ratio override)"
            elif contour_dark_ratio < 0.85 and dark_ratio < 0.80:
                decision = "REJECT (contour ratio override)"
            elif contour_dark_ratio >= 0.80 and dark_ratio >= 0.70 and touches and ratio > 0.9:
                accepted, decision = True, "ACCEPT (relaxed contour-touch override)"
            else:
                accepted, decision = False, "REJECT (not enough evidences)"

        self.logger.debug(
            f"grid_detection,{area:.1f},{dark_ratio:.3f},{contour_dark_ratio:.3f},{min_ratio:.3f},"
            f"{length:.1f},{line_orientation},{angle:.2f},{decision},{int(touches)},{ratio:.2f}"
        )

        if accepted:
            status = DetectionStatus.ACCEPT
        elif maybe:
            status = DetectionStatus.MAYBE
        else:
            status = DetectionStatus.REJECT

        return status, rotated_box
